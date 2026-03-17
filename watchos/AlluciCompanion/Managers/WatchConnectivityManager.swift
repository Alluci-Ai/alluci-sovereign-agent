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
    
    func session(_ session: WCSession, activationDidCompleteWith activationState: WCSessionActivationState, error: Error?) {
        DispatchQueue.main.async {
            self.isReachable = session.isReachable
        }
    }
    
    func sessionDidBecomeInactive(_ session: WCSession) {}
    func sessionDidDeactivate(_ session: WCSession) {
        session.activate()
    }
    
    private let sender = TelemetrySender()
    
    func session(_ session: WCSession, didReceiveMessage message: [String : Any]) {
        if let hr = message["hr"] as? Int, let hrv = message["hrv"] as? Int {
            let sample = TelemetrySample(hr: hr, hrv: hrv)
            DispatchQueue.main.async {
                self.lastReceivedVitals = sample
            }
            
            // Forward to backend
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
    let hr: Int?
    let hrv: Int?
    var timestamp: String? = nil
}
