import Foundation

struct MotionResult {
    let state: String
    let effect: String
}

struct MotionTracker {
    private var run: String?
    private var wasComplete = false
    private var seenAttention = Set<String>()
    private var seenEvents = Set<String>()

    mutating func observe(_ data: [String:Any]) -> MotionResult {
        let key = data["run_key"] as? String ?? data["run_id"] as? String ?? "snapshot"
        let workers = data["workers"] as? [[String:Any]] ?? []
        let requests = data["approvals"] as? [[String:Any]] ?? []
        var attention = requests.compactMap { ($0["fingerprint"] as? String).map { "request:" + $0 } }
        attention += workers.filter { ["blocked","paused","failed"].contains($0["state"] as? String ?? "") }.map {
            "worker:\($0["id"] ?? ""):\($0["state"] ?? ""):\($0["watchdog"] ?? "")"
        }
        let events = (data["activity"] as? [[String:Any]] ?? []).map { event in
            ["agent","at","kind","text","sequence"].map { String(describing:event[$0] ?? "") }.joined(separator:"\u{1f}")
        }
        let complete = data["all_done"] as? Bool ?? false
        var effect = "none"
        if run == key {
            if attention.contains(where: { !seenAttention.contains($0) }) { effect = "attention" }
            else if !wasComplete && complete && attention.isEmpty { effect = "complete" }
            else if events.contains(where: { !seenEvents.contains($0) }) { effect = "log" }
        } else {
            seenAttention.removeAll(); seenEvents.removeAll()
        }
        seenAttention.formUnion(attention); seenEvents.formUnion(events)
        if seenEvents.count > 1000 { seenEvents = Set(events) }
        run = key; wasComplete = complete
        let active = workers.contains { ["running","dispatching"].contains($0["state"] as? String ?? "") && ($0["awaiting_approval"] as? Bool) != true && ($0["awaiting_supervisor"] as? Bool) != true }
        return MotionResult(state: !attention.isEmpty ? "attention" : complete ? "complete" : active ? "working" : "idle", effect:effect)
    }
}
