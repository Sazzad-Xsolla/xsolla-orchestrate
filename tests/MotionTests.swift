import Foundation

@main struct MotionTests {
    static func main() {
        var tracker=MotionTracker()
        var data:[String:Any]=["run_key":"one","approvals":[],"workers":[],"activity":[],"all_done":false]
        assert(tracker.observe(data).effect=="none")
        data["approvals"]=[["fingerprint":"request-1"]]
        assert(tracker.observe(data).effect=="attention")
        assert(tracker.observe(data).effect=="none")
        data["approvals"]=[["fingerprint":"request-2"]]
        assert(tracker.observe(data).effect=="attention")
        data["approvals"]=[]
        assert(tracker.observe(data).state=="idle")
        data["activity"]=[["at":"now","agent":"pip","kind":"text","text":"Reading catalog"]]
        assert(tracker.observe(data).effect=="log")
        assert(tracker.observe(data).effect=="none")
        data["all_done"]=true
        assert(tracker.observe(data).effect=="complete")
        assert(tracker.observe(data).effect=="none")
        data["run_key"]="two"
        assert(tracker.observe(data).effect=="none")
        data["workers"]=[["id":"pip","state":"failed"]]
        assert(tracker.observe(data).effect=="attention")
        assert(tracker.observe(data).effect=="none")
        assert(tracker.observe(data).state=="attention")
        print("13 native motion assertions passed")
    }
}
