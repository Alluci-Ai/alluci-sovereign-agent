import Foundation

/// Matches the Python backend Pydantic model:
/// class OfflineInteraction(BaseModel):
///     id: str
///     timestamp: str
///     user_prompt: str
///     agent_response: str
///     inferred_intent: Optional[str] = None
struct OfflineInteraction: Codable {
    let id: String
    let timestamp: String
    let user_prompt: String
    let agent_response: String
    let inferred_intent: String?
}

/// Matches the Python backend payload structure
struct EdgeRecoveryPayload: Codable {
    let device_id: String
    let interactions: [OfflineInteraction]
}

class OfflineQueueManager {
    static let shared = OfflineQueueManager()
    
    private let fileManager = FileManager.default
    private let queueFileName = "edge_recovery_queue.json"
    
    private var queueURL: URL {
        let documentDirectory = fileManager.urls(for: .documentDirectory, in: .userDomainMask).first!
        return documentDirectory.appendingPathComponent(queueFileName)
    }
    
    private init() {}
    
    /// Appends a new offline interaction to the disk safely.
    func enqueue(prompt: String, response: String, intent: String? = nil) {
        var currentQueue = getQueue()
        
        let formatter = ISO8601DateFormatter()
        let timestamp = formatter.string(from: Date())
        
        let newInteraction = OfflineInteraction(
            id: UUID().uuidString,
            timestamp: timestamp,
            user_prompt: prompt,
            agent_response: response,
            inferred_intent: intent
        )
        
        currentQueue.append(newInteraction)
        saveQueue(currentQueue)
        print("[OfflineQueueManager] Enqueued new offline interaction. Total items: \(currentQueue.count)")
    }
    
    /// Fetches the current queue from disk.
    private func getQueue() -> [OfflineInteraction] {
        guard fileManager.fileExists(atPath: queueURL.path),
              let data = try? Data(contentsOf: queueURL),
              let queue = try? JSONDecoder().decode([OfflineInteraction].self, from: data) else {
            return []
        }
        return queue
    }
    
    /// Atomically saves the queue to disk to prevent corruption on crash.
    private func saveQueue(_ queue: [OfflineInteraction]) {
        do {
            let data = try JSONEncoder().encode(queue)
            let tempURL = fileManager.temporaryDirectory.appendingPathComponent(UUID().uuidString)
            
            // Write to temporary location first
            try data.write(to: tempURL, options: .atomic)
            
            // Atomically move it to replace the old file
            _ = try? fileManager.removeItem(at: queueURL)
            try fileManager.moveItem(at: tempURL, to: queueURL)
        } catch {
            print("[OfflineQueueManager] Failed to save queue: \(error)")
        }
    }
    
    /// Clears the queue after a successful backend ingestion.
    func clearQueue() {
        do {
            if fileManager.fileExists(atPath: queueURL.path) {
                try fileManager.removeItem(at: queueURL)
                print("[OfflineQueueManager] Queue successfully cleared.")
            }
        } catch {
            print("[OfflineQueueManager] Failed to clear queue: \(error)")
        }
    }
    
    /// Attempts to POST the queued events to the Workstation using a background URLSession.
    func offloadQueue(baseURL: String, token: String) {
        let currentQueue = getQueue()
        guard !currentQueue.isEmpty else {
            print("[OfflineQueueManager] Queue is empty. Nothing to offload.")
            return
        }
        
        guard let url = URL(string: "\(baseURL)/api/v1/sync/edge-recovery") else {
            print("[OfflineQueueManager] Invalid base URL for sync.")
            return
        }
        
        let payload = EdgeRecoveryPayload(
            device_id: "IPHONE_17_PRO",
            interactions: currentQueue
        )
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        do {
            let body = try JSONEncoder().encode(payload)
            request.httpBody = body
            
            let config = URLSessionConfiguration.background(withIdentifier: "ai.alluci.companion.sync.\(UUID().uuidString)")
            config.isDiscretionary = false
            config.sessionSendsLaunchEvents = true
            let session = URLSession(configuration: config, delegate: SyncSessionDelegate(manager: self), delegateQueue: nil)
            
            // For background sessions, use uploadTask
            let tempDir = fileManager.temporaryDirectory
            let tempFileURL = tempDir.appendingPathComponent(UUID().uuidString)
            try body.write(to: tempFileURL)
            
            let task = session.uploadTask(with: request, fromFile: tempFileURL)
            task.resume()
            print("[OfflineQueueManager] Offload background task submitted for \(currentQueue.count) interactions.")
            
        } catch {
            print("[OfflineQueueManager] Failed to encode offload payload: \(error)")
        }
    }
}

class SyncSessionDelegate: NSObject, URLSessionTaskDelegate {
    let manager: OfflineQueueManager
    
    init(manager: OfflineQueueManager) {
        self.manager = manager
    }
    
    func urlSession(_ session: URLSession, task: URLSessionTask, didCompleteWithError error: Error?) {
        if let error = error {
            print("[SyncSessionDelegate] Sync failed: \(error.localizedDescription)")
            return
        }
        
        if let httpResponse = task.response as? HTTPURLResponse, httpResponse.statusCode == 200 {
            print("[SyncSessionDelegate] 200 OK Received. Sync successful.")
            manager.clearQueue()
        } else {
            let statusCode = (task.response as? HTTPURLResponse)?.statusCode ?? 0
            print("[SyncSessionDelegate] Sync failed with status: \(statusCode)")
        }
    }
}
