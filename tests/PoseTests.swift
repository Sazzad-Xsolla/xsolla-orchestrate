import Foundation

@main struct PoseTests {
    static func main() {
        func sample(_ time: Double, _ state: String = "idle", _ effect: String = "none", _ reduced: Bool = false) -> PoseSample {
            MotionPose.sample(state: state, effect: effect, effectTime: 0.5, clock: time, reduced: reduced)
        }
        // Check visible stability across every state and event, not just the seam.
        for time in stride(from: 0.0, through: 30.0, by: 0.01) {
            let pose = sample(time)
            assert(pose.row == 0 && pose.frame == 0)
            assert(pose.scaleY >= 1 && pose.scaleY <= 1 + MotionPose.breathAmplitude)
            assert(abs(sample(time + 1.0/60).scaleY - pose.scaleY) * 140 < 0.006)
            for state in ["idle", "working", "attention", "complete", "failed"] {
                for effect in ["none", "attention", "complete", "log"] {
                    assert(sample(time, state, effect) == pose)
                    assert(sample(time, state, effect, true) == PoseSample(row: 0, frame: 0))
                }
            }
        }
        for cycle in 1...5 {
            let seam = Double(cycle) * MotionPose.breathPeriod
            assert(abs(sample(seam - 0.0001).scaleY - sample(seam + 0.0001).scaleY) < 0.0000001)
        }
        assert(sample(0).scaleY == 1)
        assert(abs(sample(MotionPose.breathPeriod / 2).scaleY - 1 - MotionPose.breathAmplitude) < 0.0000001)
        print("Stable artwork, bounded continuous breathing, state continuity and reduced motion passed")
    }
}
