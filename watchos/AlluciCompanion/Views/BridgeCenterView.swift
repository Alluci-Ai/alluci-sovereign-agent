import SwiftUI

struct BridgeCenterView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                BridgeSection(title: "Apple Ecosystem", bridges: [
                    ("iMessage", "P2P", "Connected"),
                    ("iCloud", "Drive", "Connected"),
                    ("iWatch", "Sensor", "Connected")
                ])
                BridgeSection(title: "Social Manifold", bridges: [
                    ("Telegram", "E2EE", "Connected"),
                    ("Signal", "E2EE", "Connected"),
                    ("WhatsApp", "Chat", "Offline"),
                    ("X (Twitter)", "Public", "Connected"),
                    ("Discord", "Community", "Offline")
                ])
                BridgeSection(title: "Enterprise Core", bridges: [
                    ("Slack", "Workspace", "Offline"),
                    ("Gmail", "Email", "Connected"),
                    ("GDrive", "Storage", "Connected")
                ])
                BridgeSection(title: "Verus Identity", bridges: [
                    ("VerusID", "Sovereign Identity", "Connected")
                ])
            }
            .padding()
        }
        .navigationTitle("Bridges")
    }
}

struct BridgeSection: View {
    let title: String
    let bridges: [(String, String, String)]
    
    var body: some View {
        VStack(alignment: .leading) {
            Text(title).font(.headline).foregroundColor(.secondary)
                .padding(.bottom, 4)
            
            VStack(spacing: 0) {
                ForEach(bridges.indices, id: \.self) { index in
                    let b = bridges[index]
                    BridgeRow(name: b.0, type: b.1, status: b.2)
                        .padding(.vertical, 8)
                    if index < bridges.count - 1 {
                        Divider()
                    }
                }
            }
            .padding()
            .background(Color(.secondarySystemGroupedBackground))
            .cornerRadius(10)
        }
    }
}

struct BridgeRow: View {
    let name: String
    let type: String
    let status: String
    
    var body: some View {
        HStack {
            VStack(alignment: .leading) {
                Text(name).font(.headline)
                Text(type).font(.caption).foregroundColor(.secondary)
            }
            Spacer()
            Text(status)
                .font(.caption)
                .foregroundColor(status == "Connected" ? .green : .gray)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(status == "Connected" ? Color.green.opacity(0.1) : Color.gray.opacity(0.1))
                .cornerRadius(8)
        }
    }
}
