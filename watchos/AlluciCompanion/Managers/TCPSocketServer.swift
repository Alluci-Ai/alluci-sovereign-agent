import Foundation
import Network

class TCPSocketServer: ObservableObject {
    static let shared = TCPSocketServer()
    
    private var listener: NWListener?
    private var activeConnection: NWConnection?
    private var connections: [NWConnection] = []
    
    let voiceManager = VoiceManager()
    let notificationManager = NotificationManager()
    
    // Determine Hardware Tier for VoiceOrchestrator
    private var hardwareTier: String {
        #if os(watchOS)
        return "Hardware-Tier: WATCH_EXTREME_EDGE"
        #else
        // In a real app we'd use UIDevice.current.model
        return "Hardware-Tier: IOS_COMPANION_LOW_POWER"
        #endif
    }
    
    func start(port: UInt16 = 8124) {
        do {
            let tcpOptions = NWProtocolTCP.Options()
            let parameters = NWParameters(tls: nil, tcp: tcpOptions)
            
            listener = try NWListener(using: parameters, on: NWEndpoint.Port(rawValue: port)!)
            listener?.newConnectionHandler = { [weak self] newConnection in
                self?.handleNewConnection(newConnection)
            }
            listener?.start(queue: .main)
            print("TCPSocketServer listening on port \(port)")
        } catch {
            print("Failed to start socket server: \(error)")
        }
    }
    
    private func handleNewConnection(_ connection: NWConnection) {
        connections.append(connection)
        activeConnection = connection
        connection.start(queue: .main)
        
        // Broadcast Hardware Tier upon connection
        if let tierData = "\(hardwareTier)\n".data(using: .utf8) {
            connection.send(content: tierData, completion: .contentProcessed({ _ in }))
        }
        
        receiveMessage(on: connection)
    }
    
    func send(data: Data) {
        activeConnection?.send(content: data, completion: .contentProcessed({ error in
            if let error = error { print("Send error: \(error)") }
        }))
    }
    
    private func receiveMessage(on connection: NWConnection) {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 65536) { [weak self] data, context, isComplete, error in
            if let data = data, !data.isEmpty {
                self?.processInboundPayload(data)
            }
            
            if error == nil && !isComplete {
                self?.receiveMessage(on: connection)
            } else {
                self?.connections.removeAll { $0 === connection }
                if self?.activeConnection === connection { self?.activeConnection = nil }
            }
        }
    }
    
    struct SocketPayload: Codable {
        let body: String?
        let recipient: String?
        let text: String?
    }
    
    private func processInboundPayload(_ data: Data) {
        // Simple heuristic: Try to decode as UTF8 JSON string. If it fails, assume it's a binary PCM chunk.
        guard let payloadString = String(data: data, encoding: .utf8) else {
            // Binary audio streaming (Kokoro PCM 48kHz or Opus)
            DispatchQueue.main.async {
                self.voiceManager.playIncomingPCM(data)
            }
            return
        }
        
        let lines = payloadString.components(separatedBy: "\n").filter { !$0.isEmpty }
        for line in lines {
            guard let lineData = line.data(using: .utf8) else { continue }
            processPayload(data: lineData)
        }
    }

    private func processPayload(data: Data) {
        let decoder = JSONDecoder()
        do {
            let payload = try decoder.decode(SocketPayload.self, from: data)
            print("Decoded valid socket payload: \(payload)")
            
            // Route payloads natively
            if let body = payload.body {
                if body.contains("text_for_native_tts") {
                    if let text = payload.text, !text.isEmpty {
                        DispatchQueue.main.async {
                            self.voiceManager.speak(text: text)
                        }
                    }
                } else if body.contains("DEEP_WORK") || body.contains("PEAK_PERFORMANCE") {
                    DispatchQueue.main.async {
                        self.notificationManager.sendNotification(title: "Agent Mode Shift", body: body)
                    }
                }
            }
        } catch {
            print("Failed to strictly decode payload: \(error)")
        }
    }
}
