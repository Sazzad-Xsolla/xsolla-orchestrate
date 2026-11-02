import Foundation

struct PoseSample: Equatable {
    let row: Int
    let frame: Int
    let scaleY: Double

    init(row: Int, frame: Int, scaleY: Double = 1) {
        self.row = row
        self.frame = frame
        self.scaleY = scaleY
    }
}

enum MotionPose {
    // Independently drawn poses change silhouette and registration. Keep one
    // drawing and use continuous, foot-anchored breathing instead of ping-pong.
    static let breathPeriod = 5.6
    static let breathAmplitude = 0.004

    static func sample(state: String, effect: String, effectTime: Double, clock: Double, reduced: Bool) -> PoseSample {
        let phase = max(0, clock).truncatingRemainder(dividingBy: breathPeriod) / breathPeriod
        let breath = reduced ? 0 : breathAmplitude * (1 - cos(2 * Double.pi * phase)) / 2
        // State changes are conveyed by the existing label, envelope and notice.
        // They must not replace the artwork or reset the breathing clock.
        return PoseSample(row: 0, frame: 0, scaleY: 1 + breath)
    }
}
