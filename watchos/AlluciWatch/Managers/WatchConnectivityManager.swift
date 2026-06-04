import Foundation
import WatchConnectivity
import AVFoundation
import WatchKit

class WatchConnectivityManager: NSObject, ObservableObject, WCSessionDelegate {
    @Published var isReachable: Bool = false
    private let synthesizer = AVSpeechSynthesizer()
    
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
    
    func sessionReachabilityDidChange(_ session: WCSession) {
        DispatchQueue.main.async {
            self.isReachable = session.isReachable
        }
    }
    
    // Receive TTS or Notification commands from iPhone
    func session(_ session: WCSession, didReceiveMessage message: [String : Any]) {
        if let ttsText = message["tts"] as? String {
            speak(text: ttsText)
        }
        
        if let notifTitle = message["notify_title"] as? String, let notifBody = message["notify_body"] as? String {
            // Very simple mock alert via haptics for now
            WKInterfaceDevice.current().play(.notification)
            print("Watch Notification: \(notifTitle) - \(notifBody)")
        }
    }
    
    // Send biometrics to iPhone
    func sendTelemetry(hr: Int, hrv: Int) {
        guard WCSession.default.isReachable else { return }
        WCSession.default.sendMessage(["hr": hr, "hrv": hrv], replyHandler: nil) { error in
            print("WCSession Error sending telemetry: \(error.localizedDescription)")
        }
    }
    
    private func speak(text: String) {
        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = AVSpeechSynthesisVoice(language: "en-US")
        synthesizer.speak(utterance)
    }
}
