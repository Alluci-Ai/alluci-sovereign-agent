import Foundation
import CoreBluetooth
import Network

enum RoutingState {
    case tethered       // Local Wi-Fi + Desktop in range -> Stream PCM
    case cellularProxy  // Cellular / Remote -> Stream Text only
    case offlineFallback// Offline -> Local MLX inference
}

class ContextRouter: NSObject, ObservableObject, CBCentralManagerDelegate {
    @Published var isDesktopInRange: Bool = false
    @Published var currentRoute: RoutingState = .offlineFallback
    
    private var centralManager: CBCentralManager!
    private let desktopBeaconUUID = CBUUID(string: "A1B2C3D4-E5F6-47A8-9012-3456789ABCDE")
    
    private let pathMonitor = NWPathMonitor()
    private let monitorQueue = DispatchQueue(label: "NetworkMonitor")
    @Published var isWiFi: Bool = false
    @Published var isCellular: Bool = false
    @Published var isConnected: Bool = false
    
    override init() {
        super.init()
        self.centralManager = CBCentralManager(delegate: self, queue: nil)
        
        pathMonitor.pathUpdateHandler = { path in
            DispatchQueue.main.async {
                self.isConnected = path.status == .satisfied
                self.isWiFi = path.usesInterfaceType(.wifi)
                self.isCellular = path.usesInterfaceType(.cellular)
                self.updateRoutingState()
            }
        }
        pathMonitor.start(queue: monitorQueue)
    }
    
    private func updateRoutingState() {
        if isDesktopInRange && (isWiFi || isConnected) {
            currentRoute = .tethered
        } else if isConnected {
            currentRoute = .cellularProxy
        } else {
            currentRoute = .offlineFallback
        }
        print("ContextRouter switched to: \(currentRoute)")
    }
    
    func routePrompt(_ text: String, completion: @escaping (String) -> Void) {
        switch currentRoute {
        case .tethered:
            print("Routing to Desktop Core (Gemma 4) - TETHERED")
            // Send text over WebSocket (placeholder)
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                completion("Response from Desktop Core (Tethered).")
            }
        case .cellularProxy:
            print("Routing to Desktop Core (Gemma 4) - CELLULAR PROXY")
            // Send text over Tailscale/VPN (placeholder)
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                completion("Response from Desktop Core (Cellular).")
            }
        case .offlineFallback:
            print("Routing to Local Inference Engine (Gemma 2B MLX)")
            LocalInferenceManager.shared.generateResponse(prompt: text) { response in
                completion(response)
            }
        }
    }
    
    // MARK: - CBCentralManagerDelegate
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        if central.state == .poweredOn {
            centralManager.scanForPeripherals(withServices: [desktopBeaconUUID], options: [CBCentralManagerScanOptionAllowDuplicatesKey: true])
        } else {
            DispatchQueue.main.async {
                self.isDesktopInRange = false
                self.updateRoutingState()
            }
        }
    }
    
    func centralManager(_ central: CBCentralManager, didDiscover peripheral: CBPeripheral, advertisementData: [String : Any], rssi RSSI: NSNumber) {
        if RSSI.intValue > -85 {
            DispatchQueue.main.async {
                if !self.isDesktopInRange {
                    self.isDesktopInRange = true
                    self.updateRoutingState()
                }
            }
        } else {
            DispatchQueue.main.async {
                if self.isDesktopInRange {
                    self.isDesktopInRange = false
                    self.updateRoutingState()
                }
            }
        }
    }
}
