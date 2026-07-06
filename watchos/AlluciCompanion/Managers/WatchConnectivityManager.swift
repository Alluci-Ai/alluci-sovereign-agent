import Foundation
import WatchConnectivity

class WatchConnectivityManager: NSObject, ObservableObject, WCSessionDelegate {
    @Published var isReachable: Bool = false
    @Published var lastReceivedVitals: TelemetrySample?
    
    override init() {
        super.init()
        if WCSession.isSupported() {
            let session = WCSession.default
            session.delegate = self
            session.activate()
        }
    }
    
        DispatchQueue.main.async {
            self.isReachable = session.isReachable
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
            }
        } else {
            print("WCSession unreachable. Cannot send payload.")
        }
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
        
        if let voicePrompt = voice {
            // Intercept voice command and hand off to HybridRouter
            HybridRouter.shared.routeVoiceCommand(voicePrompt) { agentResponse in
                print("[WatchConnectivityManager] Sending response back to Watch: \(agentResponse)")
                // Send response payload back to the Watch
                let replyPayload = ["agentResponse": agentResponse]
                self.sendPayloadToiPhone(payload: replyPayload) // Note: Method name is sendPayloadToiPhone but it's used bidirectionally in the prototype
            }
        }
        
        // Forward biometrics to backend
        if hr != nil || hrv != nil {
            Task {
                await sender.sendTelemetry(sample: sample)
            }
        }
    }
    
    func sessionReachabilityDidChange(_ session: WCSession) {
        DispatchQueue.main.async {
            self.isReachable = session.isReachable
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
