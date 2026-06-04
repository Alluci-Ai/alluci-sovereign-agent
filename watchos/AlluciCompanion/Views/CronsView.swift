import SwiftUI

struct CronsView: View {
    @State private var crons = [
        (name: "Daily Crypto Fetch", schedule: "0 8 * * *", enabled: true),
        (name: "System Health Check", schedule: "*/15 * * * *", enabled: true)
    ]
    
    var body: some View {
        ScrollView {
            VStack(spacing: 12) {
                ForEach($crons, id: \.name) { $cron in
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text(cron.name).font(.headline)
                            Spacer()
                            Toggle("", isOn: $cron.enabled).labelsHidden()
                        }
                        Text("Cron: \(cron.schedule)").font(.caption).foregroundColor(.secondary)
                    }
                    .padding()
                    .background(Color(.secondarySystemGroupedBackground))
                    .cornerRadius(12)
                }
            }
            .padding()
        }
        .navigationTitle("Cron Jobs")
    }
}
