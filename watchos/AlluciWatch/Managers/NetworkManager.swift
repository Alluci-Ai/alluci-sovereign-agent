import Foundation

class NetworkManager: ObservableObject {
    @Published var isPaired: Bool = false
    @Published var sessionToken: String?
    @Published var baseURL: String = ""
    @Published var deviceID: String = ""
    
    private let defaults = UserDefaults.standard
    
    init() {
        self.sessionToken = defaults.string(forKey: "sessionToken")
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
                
                self.defaults.set(result.session_token, forKey: "sessionToken")
                self.defaults.set(url, forKey: "baseURL")
                self.defaults.set(deviceID, forKey: "deviceID")
            }
        } else {
            throw NSError(domain: "Pairing", code: 401, userInfo: [NSLocalizedDescriptionKey: result.error ?? "Unknown error"])
        }
    }
    
    func sendTelemetry(samples: [TelemetrySample]) async throws {
        guard let token = sessionToken, let url = URL(string: "\(baseURL)/api/bridge/iwatch/biometrics") else {
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
            self.defaults.removeObject(forKey: "sessionToken")
        }
    }
}

struct PairingResponse: Codable {
    let status: String
    let session_token: String?
    let device_id: String?
    let error: String?
}
