import SwiftUI
import WatchKit

struct ContentView: View {
    @EnvironmentObject var watchManager: WatchConnectivityManager
    @StateObject var healthManager = HealthKitManager()
    
    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                // Harmonic Gauge
                Gauge(value: 85, in: 0...100) {
                    Text("Harmonic")
                } currentValueLabel: {
                    Text("85")
                        .foregroundColor(.green)
                }
                .gaugeStyle(.circular)
                .tint(Gradient(colors: [.blue, .green]))
                
                // Affective Glance
                HStack(spacing: 12) {
                    VStack {
                        Text("HR")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                        Text("\(Int(healthManager.lastHeartRate))")
                            .font(.title3)
                            .fontWeight(.bold)
                            .foregroundColor(.red)
                    }
                    VStack {
                        Text("HRV")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                        Text("\(Int(healthManager.lastHRV))")
                            .font(.title3)
                            .fontWeight(.bold)
                            .foregroundColor(.purple)
                    }
                }
                .padding()
                .background(.ultraThinMaterial)
                .cornerRadius(12)
                
                // Voice Node
                Button(action: {
                    WKInterfaceDevice.current().play(.click)
                }) {
                    Image(systemName: "mic.fill")
                        .font(.title)
                        .padding()
                        .background(Color.blue)
                        .clipShape(Circle())
                }
                .buttonStyle(.plain)
                
                // Background Streaming Toggle
                Button(healthManager.isActiveSession ? "Stop Stream" : "Start Live Stream") {
                    if healthManager.isActiveSession {
                        healthManager.stopActiveSession()
                    } else {
                        healthManager.startActiveSession()
                    }
                }
                .buttonStyle(.borderedProminent)
                .tint(healthManager.isActiveSession ? .red : .green)
            }
        }
        .onAppear {
            healthManager.requestAuthorization()
        }
    }
}
