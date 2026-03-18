import Foundation
import Security

class TelemetrySender: ObservableObject {
    private let defaults = UserDefaults.standard
    private let keychainService = "com.alluci.agent.token"
    private let keychainAccount = "sessionToken"
    
    func sendTelemetry(sample: TelemetrySample) async {
        guard let baseURL = loadBaseURLFromKeychain(),
              let token = loadTokenFromKeychain(),
              let url = URL(string: "\(baseURL)/api/v1/channels/iwatch/biometrics") else {
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        do {
            let body = ["samples": [sample]]
            request.httpBody = try JSONEncoder().encode(body)
            
            let (_, response) = try await URLSession.shared.data(for: request)
            if let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) {
                print("[TELEMETRY] Successfully forwarded to backend")
            }
        } catch {
            print("[TELEMETRY] Error forwarding: \(error)")
        }
    }
    
    private func loadTokenFromKeychain() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: keychainAccount,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        
        var dataTypeRef: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &dataTypeRef)
        
        if status == errSecSuccess, let data = dataTypeRef as? Data, let token = String(data: data, encoding: .utf8) {
            return token
        }
        return nil
    }
    
    private func loadBaseURLFromKeychain() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: "baseURL",
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        
        var dataTypeRef: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &dataTypeRef)
        
        if status == errSecSuccess, let data = dataTypeRef as? Data, let urlStr = String(data: data, encoding: .utf8) {
            return urlStr
        }
        return nil
    }
}
