import Foundation
import Network

class HybridRouter {
    static let shared = HybridRouter()
    
    private let monitor = NWPathMonitor()
    private let queue = DispatchQueue(label: "HybridRouterMonitor")
    
    /// Tracks whether we have a direct, active path to the Workstation.
    /// Simplified to generic internet connection for this prototype.
    private var isWorkstationReachable: Bool = false
    
    private init() {
        monitor.pathUpdateHandler = { [weak self] path in
            if path.status == .satisfied {
                self?.isWorkstationReachable = true
                print("[HybridRouter] Workstation is Reachable. State A (Online).")
                // Whenever we regain connection, immediately try to flush the offline queue!
                self?.triggerSync()
            } else {
                self?.isWorkstationReachable = false
                print("[HybridRouter] Workstation is Unreachable. State B (Offline).")
            }
        }
        monitor.start(queue: queue)
    }
    
    /// Process an incoming voice command from the Apple Watch
    func routeVoiceCommand(_ prompt: String, completion: @escaping (String) -> Void) {
        if isWorkstationReachable {
            // STATE A: Online
            // Forward the command to the Workstation using WebSocket or TelemetrySender.
            // For now, we simulate the forward and receive.
            forwardToWorkstation(prompt: prompt, completion: completion)
        } else {
            // STATE B: Offline
            // Immediately run the prompt through the local Edge Model (Gemma 2B)
            print("[HybridRouter] Intercepting request. Booting Edge Model natively.")
            
            LocalInferenceManager.shared.generateResponse(prompt: prompt) { agentResponse in
                
                // Enqueue the offline interaction into the JSON buffer so it isn't lost
                OfflineQueueManager.shared.enqueue(prompt: prompt, response: agentResponse, intent: "Offline Request")
                
                // Return the response back to the Watch
                completion(agentResponse)
            }
        }
    }
    
    private func forwardToWorkstation(prompt: String, completion: @escaping (String) -> Void) {
        // Here we would implement the actual WebSocket emit or HTTP request to the Workstation.
        // For demonstration, simulating network latency:
        print("[HybridRouter] Routing command to MACBOOK_WORKSTATION...")
        DispatchQueue.global().asyncAfter(deadline: .now() + 0.5) {
            completion("Workstation 31B Model: Acknowledged -> '\(prompt)'")
        }
    }
    
    private func triggerSync() {
        // Attempt to load baseURL and token securely from Keychain
        let keychainService = "com.alluci.agent.token"
        
        let urlQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: "baseURL",
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        
        let tokenQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: "sessionToken",
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        
        var urlRef: AnyObject?
        var tokenRef: AnyObject?
        
        if SecItemCopyMatching(urlQuery as CFDictionary, &urlRef) == errSecSuccess,
           let urlData = urlRef as? Data, let baseURL = String(data: urlData, encoding: .utf8),
           SecItemCopyMatching(tokenQuery as CFDictionary, &tokenRef) == errSecSuccess,
           let tokenData = tokenRef as? Data, let token = String(data: tokenData, encoding: .utf8) {
            
            // Initiate the background sync payload
            OfflineQueueManager.shared.offloadQueue(baseURL: baseURL, token: token)
        } else {
            print("[HybridRouter] Could not retrieve Workstation credentials from Keychain. Delaying sync.")
        }
    }
}
