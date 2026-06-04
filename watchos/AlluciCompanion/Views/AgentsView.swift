import SwiftUI

struct AgentsView: View {
    @State private var agents = [
        (name: "Alluci (Primary)", status: "Working", id: "A1"),
        (name: "Research-Node", status: "Idle", id: "A2"),
        (name: "Trading-Bot", status: "Suspended", id: "A3")
    ]
    @State private var showingManageSheet = false
    @State private var selectedAgent = ""
    
    var body: some View {
        ScrollView {
            VStack(spacing: 12) {
                ForEach(agents, id: \.id) { agent in
                    HStack {
                        Image(systemName: "cpu")
                            .foregroundColor(agent.status == "Working" ? .green : .gray)
                        VStack(alignment: .leading) {
                            Text(agent.name).font(.headline)
                            Text(agent.status).font(.caption).foregroundColor(.secondary)
                        }
                        Spacer()
                        Button("Manage") {
                            selectedAgent = agent.name
                            showingManageSheet = true
                        }
                        .buttonStyle(.bordered)
                    }
                    .padding()
                    .background(Color(.secondarySystemGroupedBackground))
                    .cornerRadius(12)
                }
            }
            .padding()
        }
        .sheet(isPresented: $showingManageSheet) {
            NavigationStack {
                Form {
                    Section(header: Text("Current Configuration")) {
                        LabeledContent("Personality Tone", value: "0.8 (Formal)")
                        LabeledContent("Active Crons", value: "3")
                        LabeledContent("Current Task", value: "Vector Consolidation")
                    }
                    Section {
                        Button("Suspend Agent") {}.foregroundColor(.red)
                        Button("Wake Agent") {}
                    }
                }
                .navigationTitle(selectedAgent)
                .toolbar {
                    Button("Close") { showingManageSheet = false }
                }
            }
        }
    }
}
