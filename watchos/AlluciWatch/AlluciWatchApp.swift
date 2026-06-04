import SwiftUI

@main
struct AlluciWatch_Watch_AppApp: App {
    @StateObject var network = NetworkManager()
    @StateObject var hk = HealthKitManager()
    @StateObject var wc = WatchConnectivityManager()
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(network)
                .environmentObject(hk)
                .environmentObject(wc)
        }
    }
}
