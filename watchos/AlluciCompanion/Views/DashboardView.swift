import SwiftUI
import Charts

struct BiometricData: Identifiable {
    let id = UUID()
    let time: Date
    let value: Double
}

struct DashboardView: View {
    @StateObject private var healthKitManager = HealthKitManager()
    @State private var pvtScore: Double = 0.0 // To hold recent PVT result
    
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 20) {
                    
                    if !healthKitManager.isAuthorized {
                        Button("Authorize HealthKit") {
                            healthKitManager.requestAuthorization()
                        }
                        .buttonStyle(.borderedProminent)
                        .padding()
                    }
                    
                    // ACE Core Biometrics
                    VStack(alignment: .leading) {
                        Text("Biometric State (ACE)").font(.headline).padding(.horizontal)
                        HStack(spacing: 16) {
                            BiometricCard(title: "Heart Rate", value: healthKitManager.currentHR > 0 ? String(format: "%.0f bpm", healthKitManager.currentHR) : "---", icon: "heart.fill", color: .red)
                            BiometricCard(title: "HRV (SDNN)", value: healthKitManager.currentHRV > 0 ? String(format: "%.0f ms", healthKitManager.currentHRV) : "---", icon: "waveform.path.ecg", color: .purple)
                        }
                        .padding(.horizontal)
                    }
                    
                    // Cognitive Flow Data
                    VStack(alignment: .leading) {
                        Text("Cognitive Flow").font(.headline).padding(.horizontal)
                        HStack(spacing: 16) {
                            BiometricCard(title: "Pupil Dilation", value: "3.2mm", icon: "eye.fill", color: .blue)
                            BiometricCard(title: "Alertness (PVT)", value: pvtScore > 0 ? String(format: "%.0f ms", pvtScore) : "Pending", icon: "bolt.fill", color: .orange)
                        }
                        .padding(.horizontal)
                        
                        NavigationLink(destination: PVTView()) {
                            Text("Run PVT Test")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.bordered)
                        .padding(.horizontal)
                        .padding(.top, 8)
                    }
                    
                    // System Architecture Overview
                    VStack(alignment: .leading) {
                        Text("System Architecture").font(.headline).padding(.horizontal)
                        HStack {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Nodes: 3 Active").font(.caption)
                                Text("DAG Depth: 12").font(.caption)
                                Text("Core Load: 45%").font(.caption)
                            }
                            Spacer()
                            Image(systemName: "server.rack")
                                .font(.system(size: 40))
                                .foregroundColor(.secondary)
                        }
                        .padding()
                        .background(Color(.secondarySystemGroupedBackground))
                        .cornerRadius(12)
                        .padding(.horizontal)
                    }
                }
                .padding(.vertical)
            }
            .navigationTitle("ACE Engine")
            .onAppear {
                if healthKitManager.isAuthorized {
                    healthKitManager.requestAuthorization() // Will just fetch if already auth
                }
            }
            .onReceive(NotificationCenter.default.publisher(for: NSNotification.Name("PVTCompleted"))) { notification in
                if let score = notification.object as? Double {
                    self.pvtScore = score
                }
            }
        }
    }
}

struct BiometricCard: View {
    let title: String
    let value: String
    let icon: String
    let color: Color
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Image(systemName: icon).foregroundColor(color)
            Text(title)
                .font(.caption)
                .foregroundColor(.secondary)
            Text(value)
                .font(.system(.headline, design: .rounded, weight: .bold))
                .foregroundColor(color)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}
