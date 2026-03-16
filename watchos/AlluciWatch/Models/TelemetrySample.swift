import Foundation

struct TelemetrySample: Codable {
    let hr: Int?
    let hrv: Int?
    let gsr: Float?
    let respiratory_rate: Float?
    let stress_score: Float?
    let energy_level: Float?
    let sleep_efficiency: Float?
    let valence: Float?
    let arousal: Float?
    let focus: Float?
    let recorded_at: String
    
    init(
        hr: Int? = nil,
        hrv: Int? = nil,
        gsr: Float? = nil,
        respiratory_rate: Float? = nil,
        stress_score: Float? = nil,
        energy_level: Float? = nil,
        sleep_efficiency: Float? = nil,
        valence: Float? = nil,
        arousal: Float? = nil,
        focus: Float? = nil
    ) {
        self.hr = hr
        self.hrv = hrv
        self.gsr = gsr
        self.respiratory_rate = respiratory_rate
        self.stress_score = stress_score
        self.energy_level = energy_level
        self.sleep_efficiency = sleep_efficiency
        self.valence = valence
        self.arousal = arousal
        self.focus = focus
        
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        self.recorded_at = formatter.string(from: Date())
    }
}

struct TelemetryBatch: Codable {
    let samples: [TelemetrySample]
    let device_id: String
}
