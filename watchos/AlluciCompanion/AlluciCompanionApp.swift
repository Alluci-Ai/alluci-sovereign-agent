import SwiftUI

@main
struct AlluciCompanionApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

struct ContentView: View {
    @StateObject var watchManager = WatchConnectivityManager()
    
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "hand.wave.fill")
                .font(.system(size: 60))
                .foregroundColor(.blue)
            
            Text("Alluci Companion")
                .font(.largeTitle)
                .fontWeight(.bold)
            
            StatusView(label: "Watch Connection", status: watchManager.isReachable ? "ONLINE" : "OFFLINE", color: watchManager.isReachable ? .green : .red)
            
            if let lastVitals = watchManager.lastReceivedVitals {
                VStack(alignment: .leading, spacing: 10) {
                    Text("Last Vitals from Watch:")
                        .font(.headline)
                    Text("HR: \(lastVitals.hr ?? 0) BPM")
                    Text("HRV: \(lastVitals.hrv ?? 0) ms")
                }
                .padding()
                .background(Color.secondary.opacity(0.1))
                .cornerRadius(10)
            }
        }
        .padding()
    }
}

struct StatusView: View {
    let label: String
    let status: String
    let color: Color
    
    var body: some View {
        HStack {
            Text(label)
            Spacer()
            Text(status)
                .fontWeight(.bold)
                .foregroundColor(color)
        }
        .padding()
        .background(Color.secondary.opacity(0.1))
        .cornerRadius(10)
    }
}
