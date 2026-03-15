import Foundation
import Security

class NetworkManager: ObservableObject {
    @Published var isPaired: Bool = false
    @Published var sessionToken: String?
    @Published var baseURL: String = ""
    @Published var deviceID: String = ""
    
    private let defaults = UserDefaults.standard
    private let keychainService = "com.alluci.agent.token"
    private let keychainAccount = "sessionToken"
    
    init() {
        self.sessionToken = loadTokenFromKeychain()
        self.baseURL = defaults.string(forKey: "baseURL") ?? ""
        self.deviceID = defaults.string(forKey: "deviceID") ?? ""
        self.isPaired = self.sessionToken != nil
    }
    
    func pair(url: String, deviceID: String, code: String) async throws {
        guard let requestURL = URL(string: "\(url)/api/channels/iwatch/pair") else {
            throw URLError(.badURL)
        }
        
        var request = URLRequest(url: requestURL)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body = ["device_id": deviceID, "code": code]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
            throw URLError(.badServerResponse)
        }
        
        let result = try JSONDecoder().decode(PairingResponse.self, from: data)
        if result.status == "SUCCESS" {
            DispatchQueue.main.async {
                self.sessionToken = result.session_token
                self.baseURL = url
                self.deviceID = deviceID
                self.isPaired = true
                
                if let token = result.session_token {
                    self.saveTokenToKeychain(token)
                }
                self.defaults.set(url, forKey: "baseURL")
                self.defaults.set(deviceID, forKey: "deviceID")
            }
        } else {
            throw NSError(domain: "Pairing", code: 401, userInfo: [NSLocalizedDescriptionKey: result.error ?? "Unknown error"])
        }
    }
    
    func sendTelemetry(samples: [TelemetrySample]) async throws {
        guard let token = sessionToken, let url = URL(string: "\(baseURL)/api/channels/iwatch/biometrics") else {
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let batch = TelemetryBatch(samples: samples, device_id: deviceID)
        request.httpBody = try JSONEncoder().encode(batch)
        
        let (_, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
            throw URLError(.badServerResponse)
        }
    }
    
    func unpair() {
        DispatchQueue.main.async {
            self.sessionToken = nil
            self.isPaired = false
            self.deleteTokenFromKeychain()
        }
    }
    
    // MARK: - Keychain Helpers
    
    private func saveTokenToKeychain(_ token: String) {
        guard let data = token.data(using: .utf8) else { return }
        
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: keychainAccount,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlock
        ]
        
        SecItemDelete(query as CFDictionary)
        SecItemAdd(query as CFDictionary, nil)
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
    
    private func deleteTokenFromKeychain() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: keychainAccount
        ]
        SecItemDelete(query as CFDictionary)
    }
}

struct PairingResponse: Codable {
    let status: String
    let session_token: String?
    let device_id: String?
    let error: String?
}
