import Foundation
import Network

class MDNSListener: NSObject, ObservableObject, NetServiceDelegate {
    private var netService: NetService?
    
    override init() {
        super.init()
    }
    
    func startBroadcasting(port: Int) {
        // Broadcast the mDNS service for the Python `iphone.py` zero-conf bridge
        netService = NetService(domain: "local.", type: "_alluci-iphone._tcp.", name: "AlluciCompanion", port: Int32(port))
        netService?.delegate = self
        netService?.publish()
    }
    
    func stopBroadcasting() {
        netService?.stop()
        netService = nil
    }
    
    func netServiceDidPublish(_ sender: NetService) {
        print("mDNS: Successfully published AlluciCompanion service on port \(sender.port)")
    }
    
    func netService(_ sender: NetService, didNotPublish errorDict: [String : NSNumber]) {
        print("mDNS: Failed to publish service. Error: \(errorDict)")
    }
}
