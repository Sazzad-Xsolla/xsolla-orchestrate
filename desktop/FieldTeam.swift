import AppKit
import WebKit

func tint(_ hex: UInt32) -> NSColor {
    NSColor(srgbRed: CGFloat((hex >> 16) & 255)/255, green: CGFloat((hex >> 8) & 255)/255, blue: CGFloat(hex & 255)/255, alpha: 1)
}
let teal = tint(0x141d1f), cyan = tint(0x80eaff), amber = tint(0xffc380)

class TeamPanel: NSPanel {
    override var canBecomeKey: Bool { true }
    override func cancelOperation(_ sender: Any?) { orderOut(nil) }
}

class CompanionView: NSView {
    var onClick: (() -> Void)?
    var onMove: (() -> Void)?
    var attention = 0
    var active = 0
    var connected = false
    var reducedMotion = NSWorkspace.shared.accessibilityDisplayShouldReduceMotion
    var frames: [NSImage] = []
    var tracker = MotionTracker()
    var motionState = "idle"
    var effect = "none"
    var effectAt = 0.0
    var anchor = NSPoint.zero
    var windowAnchor = NSPoint.zero
    var didDrag = false
    var timer: Timer?

    override init(frame: NSRect) {
        super.init(frame:frame)
        setAccessibilityElement(true)
        setAccessibilityRole(.button)
        setAccessibilityLabel("Field Team companion — click to open party, drag to move")
        if let url=Bundle.main.url(forResource:"motion-sprites",withExtension:"png"),
           let image=NSImage(contentsOf:url),let cg=image.cgImage(forProposedRect:nil,context:nil,hints:nil) {
            let w=CGFloat(cg.width)/4,h=CGFloat(cg.height)/2
            for row in 0..<2 { for col in 0..<4 {
                let rect=CGRect(x:CGFloat(col)*w,y:CGFloat(row)*h,width:w,height:h)
                if let part=cg.cropping(to:rect) {frames.append(NSImage(cgImage:part,size:NSSize(width:w,height:h)))}
            }}
        }
        timer=Timer.scheduledTimer(withTimeInterval:0.08,repeats:true) { [weak self] _ in
            guard let self=self,!self.reducedMotion else {return}
            self.needsDisplay=true
        }
    }
    required init?(coder:NSCoder) {fatalError("init(coder:) not supported")}
    deinit {timer?.invalidate()}
    func updateMotion(_ data:[String:Any]) {
        let result=tracker.observe(data)
        motionState=result.state
        if result.effect != "none" {effect=result.effect;effectAt=Date.timeIntervalSinceReferenceDate}
        needsDisplay=true
    }
    override func draw(_ dirtyRect:NSRect) {
        let now=Date.timeIntervalSinceReferenceDate,elapsed=now-effectAt
        let transient=elapsed<1.1 ? effect : "none"
        var col=motionState=="attention" ? 2 : motionState=="working" ? 1 : 0
        var row=0
        var hop:CGFloat=0
        if !reducedMotion {
            if transient=="complete" {col=3;row=elapsed>0.35 && elapsed<0.8 ? 1 : 0}
            else if transient=="attention" {col=2;row=elapsed>0.25 && elapsed<0.75 ? 1 : 0}
            else if motionState=="working" {row=Int(now*1.7)%2}
            else if col==0 {row=now.truncatingRemainder(dividingBy:7)>6.65 ? 1 : 0}
            if transient=="complete" || transient=="attention" {hop=CGFloat(max(0,sin(min(elapsed/0.65,1)*Double.pi)))*8}
            else if col==0 {hop=CGFloat(sin(now*1.8))*0.8}
        }
        NSGraphicsContext.current?.imageInterpolation = .none
        let index=row*4+col
        if frames.indices.contains(index) {frames[index].draw(in:NSRect(x:42,y:26+hop,width:138,height:138))}
        let box=NSRect(x:13,y:2,width:192,height:24)
        teal.setFill();NSBezierPath(rect:box).fill()
        cyan.setStroke();let border=NSBezierPath(rect:box.insetBy(dx:2,dy:2));border.lineWidth=1;border.stroke()
        let label = !connected ? "CONNECTING…" : attention>0 ? "\(active) WORKING · \(attention) NEEDS YOU" : motionState=="complete" ? "MISSION VERIFIED" : active>0 ? "\(active) AGENTS WORKING" : "TEAM READY"
        (label as NSString).draw(at:NSPoint(x:22,y:7),withAttributes:[.font:NSFont.monospacedSystemFont(ofSize:9,weight:.bold),.foregroundColor:NSColor.white])
        if attention>0 {
            amber.setFill();NSBezierPath(rect:NSRect(x:171,y:105,width:20,height:22)).fill()
            ("!" as NSString).draw(at:NSPoint(x:178,y:108),withAttributes:[.font:NSFont.monospacedSystemFont(ofSize:13,weight:.bold),.foregroundColor:teal])
        }
        if transient != "none" {
            let text=transient=="attention" ? "Your party needs you" : transient=="complete" ? "Mission complete" : "New activity"
            let rect=NSRect(x:22,y:145,width:176,height:23)
            tint(0xfffbed).setFill();NSBezierPath(rect:rect).fill()
            teal.setStroke();NSBezierPath(rect:rect).stroke()
            (text as NSString).draw(at:NSPoint(x:29,y:151),withAttributes:[.font:NSFont.monospacedSystemFont(ofSize:10,weight:.medium),.foregroundColor:teal])
        }
    }
    override func mouseDown(with event:NSEvent) {anchor=NSEvent.mouseLocation;windowAnchor=window?.frame.origin ?? .zero;didDrag=false}
    override func mouseDragged(with event:NSEvent) {
        let p=NSEvent.mouseLocation,dx=p.x-anchor.x,dy=p.y-anchor.y
        if abs(dx)+abs(dy)>4 {didDrag=true}
        guard didDrag else {return}
        let screen=NSScreen.screens.first(where:{$0.frame.contains(p)})?.visibleFrame ?? NSScreen.main!.visibleFrame
        window?.setFrameOrigin(NSPoint(x:max(screen.minX,min(windowAnchor.x+dx,screen.maxX-bounds.width)),y:max(screen.minY,min(windowAnchor.y+dy,screen.maxY-bounds.height))))
        onMove?()
    }
    override func mouseUp(with event:NSEvent) {if !didDrag {onClick?()}}
    override func accessibilityPerformPress()->Bool {onClick?();return true}
}

class AppDelegate: NSObject, NSApplicationDelegate, WKScriptMessageHandler, WKNavigationDelegate {
    var companion: CompanionView!
    var companionWindow: TeamPanel!
    var detailWindow: TeamPanel!
    var web: WKWebView!
    var statusItem: NSStatusItem!
    var polling = false
    var generation = 0
    var state: [String:Any] = [:]
    var loadedURL: URL?
    let resources = Bundle.main.resourceURL!
    var runPath: String? = UserDefaults.standard.string(forKey:"runPath")
    var skillPath: String = ""
    var dashboard: URL? { guard let text=state["dashboard"] as? String else {return nil}; return URL(string:text) }

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        let source = (try? String(contentsOf:resources.appendingPathComponent("skill-path.txt"),encoding:.utf8))?.trimmingCharacters(in:.whitespacesAndNewlines)
        let bundled=resources.appendingPathComponent("runtime").path
        let candidate=UserDefaults.standard.string(forKey:"skillPath") ?? source ?? bundled
        skillPath=FileManager.default.fileExists(atPath:candidate+"/scripts/field_team.py") ? candidate : bundled
        companionWindow=panel(NSSize(width:220,height:174),transparent:true)
        companion=CompanionView(frame:NSRect(x:0,y:0,width:220,height:174))
        companion.reducedMotion = companion.reducedMotion || UserDefaults.standard.bool(forKey:"reduceMotion")
        companion.onClick={ [weak self] in self?.toggleDetails() }
        companion.onMove={ [weak self] in self?.savePosition() }
        companionWindow.contentView=companion
        let screen=NSScreen.main!.visibleFrame
        let saved=UserDefaults.standard.array(forKey:"position") as? [Double]
        let point = saved?.count == 2 ? NSPoint(x:saved![0],y:saved![1]) : NSPoint(x:screen.maxX-260,y:screen.minY+35)
        companionWindow.setFrameOrigin(NSPoint(x:max(screen.minX,min(point.x,screen.maxX-220)),y:max(screen.minY,min(point.y,screen.maxY-174))))
        detailWindow=panel(NSSize(width:430,height:630))
        detailWindow.title="Field Team party"
        let config=WKWebViewConfiguration()
        config.userContentController.add(self,name:"fieldTeam")
        web=WKWebView(frame:.zero,configuration:config)
        web.navigationDelegate=self
        web.setValue(false,forKey:"drawsBackground")
        web.appearance=NSAppearance(named:.darkAqua)
        detailWindow.contentView=web
        statusItem=NSStatusBar.system.statusItem(withLength:NSStatusItem.variableLength)
        rebuildMenu(); showMessage("Connecting to Field Team…")
        companionWindow.orderFrontRegardless()
        NSWorkspace.shared.notificationCenter.addObserver(forName:NSWorkspace.accessibilityDisplayOptionsDidChangeNotification,object:nil,queue:.main) { [weak self] _ in
            guard let self=self else {return}
            self.companion.reducedMotion=NSWorkspace.shared.accessibilityDisplayShouldReduceMotion || UserDefaults.standard.bool(forKey:"reduceMotion")
            self.companion.needsDisplay=true;self.refresh()
        }
        refresh()
        Timer.scheduledTimer(withTimeInterval:5,repeats:true) { [weak self] _ in self?.refresh() }
    }
    func panel(_ size: NSSize, transparent: Bool=false) -> TeamPanel {
        let p=TeamPanel(contentRect:NSRect(origin:.zero,size:size),styleMask:[.borderless,.nonactivatingPanel],backing:.buffered,defer:false)
        p.level = .floating; p.isOpaque=false; p.backgroundColor=transparent ? .clear : teal
        p.hasShadow = !transparent; p.isReleasedWhenClosed=false
        p.collectionBehavior=[.canJoinAllSpaces,.fullScreenAuxiliary]
        return p
    }
    func showMessage(_ text: String) {
        let escaped=text.replacingOccurrences(of:"&",with:"&amp;").replacingOccurrences(of:"<",with:"&lt;")
        web?.loadHTMLString("<body style='background:#141d1f;color:#e8eced;font:14px -apple-system;padding:24px'><h2>Field Team</h2><p>\(escaped)</p><p>Use the menu bar to choose a run or the updated skill folder.</p></body>",baseURL:nil)
        loadedURL=nil
    }
    func savePosition() {
        let p=companionWindow.frame.origin
        UserDefaults.standard.set([Double(p.x),Double(p.y)],forKey:"position")
        if detailWindow.isVisible { positionDetails() }
    }
    func positionDetails() {
        let screen=companionWindow.screen?.visibleFrame ?? NSScreen.main!.visibleFrame
        let t=companionWindow.frame
        let x=max(screen.minX+8,min(t.maxX-430,screen.maxX-438))
        let y=max(screen.minY+8,min(t.maxY+8,screen.maxY-638))
        detailWindow.setFrameOrigin(NSPoint(x:x,y:y))
    }
    @objc func toggleDetails() {
        if detailWindow.isVisible {detailWindow.orderOut(nil)} else {positionDetails();detailWindow.makeKeyAndOrderFront(nil)}
    }
    func rebuildMenu() {
        statusItem.button?.title="FT"+(companion.attention>0 ? " · \(companion.attention)":"")
        statusItem.button?.toolTip="Xsolla Field Team"
        let menu=NSMenu()
        func add(_ title:String,_ selector:Selector) {let item=NSMenuItem(title:title,action:selector,keyEquivalent:"");item.target=self;menu.addItem(item)}
        add("Show / hide party",#selector(toggleDetails)); add("Open Mission Control",#selector(openDashboard))
        add("Choose run or project…",#selector(chooseRun)); add("Choose xsolla-orchestrate folder…",#selector(chooseSkill))
        add("Demo mode",#selector(demoMode)); add("Refresh",#selector(refresh))
        menu.addItem(.separator());add(companion.reducedMotion ? "✓ Reduce motion":"Reduce motion",#selector(toggleMotion));add("Quit Field Team",#selector(quit))
        statusItem.menu=menu;companion.menu=menu
    }
    @objc func quit() {NSApp.terminate(nil)}
    @objc func toggleMotion() {companion.reducedMotion = !companion.reducedMotion || NSWorkspace.shared.accessibilityDisplayShouldReduceMotion;UserDefaults.standard.set(companion.reducedMotion,forKey:"reduceMotion");companion.needsDisplay=true;rebuildMenu();refresh()}
    func chooseFolder(_ title:String, done:@escaping(URL)->Void) {
        let picker=NSOpenPanel();picker.title=title;picker.canChooseFiles=false;picker.canChooseDirectories=true;picker.allowsMultipleSelection=false
        picker.begin { result in if result == .OK,let url=picker.url {done(url)} }
    }
    @objc func chooseRun() {chooseFolder("Choose an xsolla-orchestrate run or project") {url in
        self.generation+=1;self.runPath=url.path;UserDefaults.standard.set(url.path,forKey:"runPath");self.loadedURL=nil;self.showMessage("Connecting to selected run…");self.refresh()
    }}
    @objc func chooseSkill() {chooseFolder("Choose the updated xsolla-orchestrate folder") {url in
        self.generation+=1;self.skillPath=url.path;UserDefaults.standard.set(url.path,forKey:"skillPath");self.loadedURL=nil;self.refresh()
    }}
    @objc func demoMode() {generation+=1;runPath=nil;UserDefaults.standard.removeObject(forKey:"runPath");loadedURL=nil;refresh()}
    @objc func openDashboard() {openMission(agent:nil)}
    func openMission(agent:String?) {
        guard var url=dashboard else {return}
        if let agent=agent {var c=URLComponents(url:url,resolvingAgainstBaseURL:false)!;c.fragment="agent="+agent;url=c.url!}
        NSWorkspace.shared.open(url)
    }
    @objc func refresh() {
        guard !polling else {return};polling=true
        let requestGeneration=generation, selectedSkill=skillPath, selectedRun=runPath
        let demoProject=FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/Xsolla Field Team/Demo").path
        DispatchQueue.global(qos:.utility).async {
            let process=Process(), pipe=Pipe()
            process.executableURL=URL(fileURLWithPath:"/usr/bin/python3")
            process.arguments=[self.resources.appendingPathComponent("bridge.py").path,"--skill",selectedSkill]+(selectedRun != nil ? ["--run",selectedRun!] : ["--demo-project",demoProject])
            process.standardOutput=pipe;process.standardError=FileHandle.nullDevice
            let deadline=DispatchWorkItem {if process.isRunning {process.terminate()}}
            var result:[String:Any]=[:]
            do {
                try process.run();DispatchQueue.global().asyncAfter(deadline:.now()+18,execute:deadline)
                let bytes=pipe.fileHandleForReading.readDataToEndOfFile();process.waitUntilExit();deadline.cancel()
                result=(try? JSONSerialization.jsonObject(with:bytes) as? [String:Any]) ?? ["error":"Cannot read run data"]
            } catch {result=["error":error.localizedDescription]}
            let object=result
            DispatchQueue.main.async {
                self.polling=false
                guard requestGeneration==self.generation else {self.refresh();return}
                if let error=object["error"] as? String {self.companion.connected=false;self.companion.motionState="idle";self.companion.effect="none";self.companion.active=0;self.companion.attention=0;self.state=[:];self.showMessage(error)} else {
                    self.state=object;self.companion.connected=true;self.companion.updateMotion(object)
                    let workers=object["workers"] as? [[String:Any]] ?? []
                    self.companion.active=workers.filter {($0["state"] as? String)=="running" && ($0["awaiting_approval"] as? Bool) != true && ($0["awaiting_supervisor"] as? Bool) != true}.count
                    self.companion.attention=(object["approvals"] as? [[String:Any]] ?? []).count+workers.filter{["blocked","paused","failed"].contains($0["state"] as? String ?? "")}.count
                    if let dashboard=self.dashboard,let url=URL(string:dashboard.absoluteString+"?widget=1&reduceMotion="+(self.companion.reducedMotion ? "1":"0")),self.loadedURL != url {self.loadedURL=url;self.web.load(URLRequest(url:url))}
                }
                self.companion.needsDisplay=true;self.rebuildMenu()
            }
        }
    }
    func userContentController(_ userContentController:WKUserContentController,didReceive message:WKScriptMessage) {
        guard message.frameInfo.isMainFrame,let origin=message.frameInfo.request.url,let expected=dashboard,
              origin.scheme==expected.scheme,origin.host==expected.host,origin.port==expected.port,
              let body=message.body as? [String:String] else {return}
        if body["action"]=="motion" {companion.reducedMotion=(body["value"]=="true") || NSWorkspace.shared.accessibilityDisplayShouldReduceMotion;UserDefaults.standard.set(companion.reducedMotion,forKey:"reduceMotion");companion.needsDisplay=true;rebuildMenu()}
        if body["action"]=="close" {detailWindow.orderOut(nil)}
        if body["action"]=="dashboard" {openMission(agent:body["agent"])}
    }
    func webView(_ webView:WKWebView,decidePolicyFor navigationAction:WKNavigationAction,decisionHandler:@escaping(WKNavigationActionPolicy)->Void) {
        guard let url=navigationAction.request.url else {decisionHandler(.cancel);return}
        if url.scheme=="about" {decisionHandler(.allow);return}
        if let expected=dashboard,url.scheme==expected.scheme,url.host==expected.host,url.port==expected.port {decisionHandler(.allow)} else {decisionHandler(.cancel)}
    }
}
@main
struct FieldTeamMain {
    static func main() {
        let application=NSApplication.shared
        let delegate=AppDelegate()
        application.delegate=delegate
        application.run()
    }
}
