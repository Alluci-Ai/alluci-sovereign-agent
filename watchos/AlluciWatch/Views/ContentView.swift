import SwiftUI

struct ContentView: View {
    @EnvironmentObject var network: NetworkManager
    @EnvironmentObject var hk: HealthKitManager
    
    @State private var isMonitoring: Bool = false
    @State private var statusMessage: String = "Idle"
    
    var body: some View {
        Group {
            if !network.isPaired {
                PairingView()
            } else {
                VStack(spacing: 8) {
                    HStack {
                        Circle()
                            .fill(isMonitoring ? Color.green : Color.gray)
                            .frame(width: 8, height: 8)
                        Text(isMonitoring ? "Monitoring" : "Ready")
                            .font(.caption)
                    }
                    
                    Text("\(Int(hk.lastHeartRate))")
                        .font(.system(size: 42, weight: .bold, design: .rounded))
                    Text("BPM")
                        .font(.caption)
                        .foregroundColor(.gray)
                    
                    Spacer()
                    
                    Button(action: {
                        toggleMonitoring()
                    }) {
                        Text(isMonitoring ? "Stop" : "Start Tracking")
                            .bold()
                    }
                    .tint(isMonitoring ? .red : .blue)
                    
                    Button(action: {
                        network.unpair()
                    }) {
                        Text("Unpair")
                            .font(.caption2)
                            .foregroundColor(.red)
                    }
                    .buttonStyle(.plain)
                    .padding(.top, 4)
                }
                .onAppear {
                    hk.requestAuthorization()
                }
            }
        }
    }
    
    func toggleMonitoring() {
        isMonitoring.toggle()
        if isMonitoring {
            hk.startHeartRateQuery { hr in
                sendUpdate()
            }
        }
    }
    
    func sendUpdate() {
        Task {
            let sample = await hk.getCurrentTelemetry()
            do {
                try await network.sendTelemetry(samples: [sample])
                statusMessage = "Synced"
            } catch {
                statusMessage = "Sync Error"
                print("Telemetry error: \(error)")
            }
        }
    }
}
