import SwiftUI

struct PairingTransferView: View {
    @StateObject private var syncManager = MultipeerSyncManager()
    @Environment(\.presentationMode) var presentationMode
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 30) {
                if !syncManager.isConnected {
                    Image(systemName: "antenna.radiowaves.left.and.right")
                        .font(.system(size: 80))
                        .foregroundColor(.blue)
                        .scaleEffect(1.1)
                        .animation(.easeInOut(duration: 1.0).repeatForever(), value: UUID())
                    
                    Text("Searching for Desktop Core...")
                        .font(.headline)
                    Text("Ensure your Mac is nearby and Bluetooth is enabled.")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                        
                    Button("Start Pairing") {
                        syncManager.startPairing()
                    }
                    .buttonStyle(.borderedProminent)
                } else if syncManager.isReceivingPayload || syncManager.incomingPayloadProgress > 0.0 {
                    Image(systemName: "lock.icloud.fill")
                        .font(.system(size: 80))
                        .foregroundColor(.green)
                        
                    Text("Receiving Core Payload")
                        .font(.headline)
                        
                    ProgressView(value: syncManager.incomingPayloadProgress, total: 1.0)
                        .progressViewStyle(LinearProgressViewStyle(tint: .green))
                        .padding(.horizontal, 40)
                        
                    Text("\(Int(syncManager.incomingPayloadProgress * 100))% Complete")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        
                    if syncManager.incomingPayloadProgress >= 1.0 {
                        Button("Finish") {
                            LocalInferenceManager.shared.loadModelWeights()
                            presentationMode.wrappedValue.dismiss()
                        }
                        .buttonStyle(.borderedProminent)
                        .padding(.top, 20)
                    }
                } else {
                    Image(systemName: "checkmark.shield.fill")
                        .font(.system(size: 80))
                        .foregroundColor(.green)
                    
                    Text("Connected to Desktop Core")
                        .font(.headline)
                    Text("Waiting for Desktop to initiate payload transfer...")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .padding()
            .navigationTitle("Secure Pairing")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        syncManager.stopPairing()
                        presentationMode.wrappedValue.dismiss()
                    }
                }
            }
        }
    }
}
