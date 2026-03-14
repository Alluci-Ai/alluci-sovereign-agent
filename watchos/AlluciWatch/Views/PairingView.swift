import SwiftUI

struct PairingView: View {
    @EnvironmentObject var network: NetworkManager
    @State private var url: String = "http://10.0.1.5:8000" // Example local IP
    @State private var deviceID: String = ""
    @State private var code: String = ""
    @State private var isScanning: Bool = false
    @State private var errorText: String?
    
    var body: some View {
        ScrollView {
            VStack(spacing: 12) {
                Text("Pair Alluci")
                    .font(.headline)
                
                TextField("Agent URL", text: $url)
                    .textContentType(.URL)
                
                TextField("Device ID", text: $deviceID)
                
                TextField("TOTP Code", text: $code)
                    .keyboardType(.numberPad)
                
                if let error = errorText {
                    Text(error)
                        .foregroundColor(.red)
                        .font(.caption2)
                }
                
                Button(action: {
                    Task {
                        do {
                            try await network.pair(url: url, deviceID: deviceID, code: code)
                        } catch {
                            errorText = error.localizedDescription
                        }
                    }
                }) {
                    Text("Connect")
                        .bold()
                }
                .background(Color.blue)
                .cornerRadius(8)
                
                Text("Scan the QR code in Settings > iWatch on your desktop agent.")
                    .font(.caption2)
                    .foregroundColor(.gray)
                    .multilineTextAlignment(.center)
            }
            .padding()
        }
    }
}
