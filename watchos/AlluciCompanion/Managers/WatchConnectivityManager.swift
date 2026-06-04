import Foundation
import WatchConnectivity

class WatchConnectivityManager: NSObject, ObservableObject, WCSessionDelegate {
    @Published var isReachable: Bool = false
    @Published var lastReceivedVitals: TelemetrySample?
    
    // Offline queue (Scenario E & F)
    private var offlinePayloadQueue: [[String: Any]] = []
    
    override init() {
        super.init()
        if WCSession.isSupported() {
            let session = WCSession.default
            session.delegate = self
            session.activate()
        }
    }
    
    func session(_ session: WCSession, activationDidCompleteWith activationState: WCSessionActivationState, error: Error?) {
        DispatchQueue.main.async {
            self.isReachable = session.isReachable
            if self.isReachable {
                self.flushQueue()
            }
        }
    }
    
    func sessionDidBecomeInactive(_ session: WCSession) {}
    func sessionDidDeactivate(_ session: WCSession) {
        session.activate()
    }
    
    private let sender = TelemetrySender()
    
    // Grouping payload transmission
    func sendPayloadToiPhone(payload: [String: Any]) {
        if WCSession.default.isReachable {
            WCSession.default.sendMessage(payload, replyHandler: nil) { error in
                print("Failed to send payload: \(error)")
                self.offlinePayloadQueue.append(payload) // Queue on failure
            }
        } else {
            // Queue for Scenario E / F
            offlinePayloadQueue.append(payload)
        }
    }
    
    // Flush queued payloads when reconnected
    private func flushQueue() {
        guard !offlinePayloadQueue.isEmpty else { return }
        for payload in offlinePayloadQueue {
            WCSession.default.sendMessage(payload, replyHandler: nil) { _ in }
        }
        offlinePayloadQueue.removeAll()
    }
    
    func session(_ session: WCSession, didReceiveMessage message: [String : Any]) {
        let hr = message["hr"] as? Int
        let hrv = message["hrv"] as? Int
        let resp = message["respiratoryRate"] as? Double
        let voice = message["voiceCommand"] as? String
        
        let sample = TelemetrySample(hr: hr, hrv: hrv, respiratoryRate: resp, voiceCommand: voice)
        DispatchQueue.main.async {
            self.lastReceivedVitals = sample
        }
        
        // Forward to backend
        Task {
            await sender.sendTelemetry(sample: sample)
        }
    }
    
    func sessionReachabilityDidChange(_ session: WCSession) {
        DispatchQueue.main.async {
            self.isReachable = session.isReachable
            if self.isReachable {
                self.flushQueue()
            }
        }
    }
}

struct TelemetrySample: Codable {
    var hr: Int?
    var hrv: Int?
    var respiratoryRate: Double?
    var voiceCommand: String?
    var timestamp: String? = nil
}
