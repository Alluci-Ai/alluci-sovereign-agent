import Foundation
import Security

struct KeychainHelper {
    static let service = "com.alluci.watch"

    static func save(_ value: String, for key: String) {
        let data = Data(value.utf8)
        let query: [String: Any] = [
            kSecClass as String:            kSecClassGenericPassword,
            kSecAttrService as String:      service,
            kSecAttrAccount as String:      key,
            kSecValueData as String:        data,
            kSecAttrAccessible as String:   kSecAttrAccessibleAfterFirstUnlock,
        ]
        SecItemDelete(query as CFDictionary)
        SecItemAdd(query as CFDictionary, nil)
    }

    static func load(for key: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String:            kSecClassGenericPassword,
            kSecAttrService as String:      service,
            kSecAttrAccount as String:      key,
            kSecMatchLimit as String:       kSecMatchLimitOne,
            kSecReturnData as String:       true,
        ]
        var result: AnyObject?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    static func delete(for key: String) {
        let query: [String: Any] = [
            kSecClass as String:       kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
        ]
        SecItemDelete(query as CFDictionary)
    }
}

class NetworkManager: ObservableObject {
    @Published var isPaired: Bool = false
    @Published var sessionToken: String?
    
    private let baseURLKey = "alluci.baseURL"
    private let deviceIDKey = "alluci.deviceID"
    private let tokenKey = "alluci.sessionToken"

    var baseURL: String {
        get { KeychainHelper.load(for: baseURLKey) ?? "https://localhost:8000" }
        set { KeychainHelper.save(newValue, for: baseURLKey) }
    }

    var deviceID: String {
        get { KeychainHelper.load(for: deviceIDKey) ?? UUID().uuidString }
        set { KeychainHelper.save(newValue, for: deviceIDKey) }
    }

    init() {
        self.sessionToken = KeychainHelper.load(for: tokenKey)
        self.isPaired = self.sessionToken != nil
    }
    
    func pair(url: String, deviceID: String, code: String) async throws {
        guard let requestURL = URL(string: "\(url)/api/v1/channels/iwatch/pair") else {
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
                    KeychainHelper.save(token, for: self.tokenKey)
                }
            }
        } else {
            throw NSError(domain: "Pairing", code: 401, userInfo: [NSLocalizedDescriptionKey: result.error ?? "Unknown error"])
        }
    }
    
    func sendTelemetry(samples: [TelemetrySample]) async throws {
        guard let token = sessionToken, let url = URL(string: "\(baseURL)/api/v1/channels/iwatch/biometrics") else {
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
            KeychainHelper.delete(for: self.tokenKey)
            KeychainHelper.delete(for: self.baseURLKey)
            KeychainHelper.delete(for: self.deviceIDKey)
        }
    }
}

struct PairingResponse: Codable {
    let status: String
    let session_token: String?
    let device_id: String?
    let error: String?
}
