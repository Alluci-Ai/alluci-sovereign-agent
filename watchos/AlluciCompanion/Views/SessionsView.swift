import SwiftUI

struct SessionsView: View {
    @State private var sessions = [
        (id: "S-102", mode: "Deep Work", duration: "2h 15m"),
        (id: "S-101", mode: "Casual Chat", duration: "45m")
    ]
    
    var body: some View {
        ScrollView {
            VStack(spacing: 12) {
                ForEach(sessions, id: \.id) { session in
                    VStack(alignment: .leading) {
                        Text("Session \(session.id)").font(.headline)
                        HStack {
                            Text(session.mode).font(.subheadline).foregroundColor(.accentColor)
                            Spacer()
                            Text(session.duration).font(.caption).foregroundColor(.secondary)
                        }
                    }
                    .padding()
                    .background(Color(.secondarySystemGroupedBackground))
                    .cornerRadius(12)
                }
            }
            .padding()
        }
        .navigationTitle("Sessions")
    }
}
