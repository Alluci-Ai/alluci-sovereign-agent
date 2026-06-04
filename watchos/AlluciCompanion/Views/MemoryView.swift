import SwiftUI

struct MemoryView: View {
    @State private var searchText = ""
    @State private var memories = [
        (content: "Working on iOS SwiftUI translations", tier: 0, id: "M1"),
        (content: "Conversation Vector: Financial Planning (Oct 12)", tier: 1, id: "M2"),
        (content: "User Preference: Prefers concise answers", tier: 2, id: "M3")
    ]
    
    var body: some View {
        ScrollView {
            VStack(spacing: 12) {
                ForEach(memories, id: \.id) { memory in
                    if searchText.isEmpty || memory.content.localizedCaseInsensitiveContains(searchText) {
                        HStack {
                            // Tier Indicator
                            Rectangle()
                                .fill(memory.tier == 0 ? Color.blue : (memory.tier == 1 ? Color.orange : Color.green))
                                .frame(width: 4)
                                .cornerRadius(2)
                            
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text(memory.tier == 0 ? "L0: Working" : (memory.tier == 1 ? "L1: Episodic" : "L2: Semantic"))
                                        .font(.caption2)
                                        .fontWeight(.bold)
                                        .foregroundColor(memory.tier == 0 ? .blue : (memory.tier == 1 ? .orange : .green))
                                        .padding(.horizontal, 6)
                                        .padding(.vertical, 2)
                                        .background((memory.tier == 0 ? Color.blue : (memory.tier == 1 ? Color.orange : Color.green)).opacity(0.15))
                                        .cornerRadius(4)
                                    Spacer()
                                    Text("ID: \(memory.id)").font(.caption2).foregroundColor(.secondary)
                                }
                                Text(memory.content).font(.subheadline)
                            }
                            .padding(.leading, 4)
                        }
                        .padding()
                        .background(Color(.secondarySystemGroupedBackground))
                        .cornerRadius(12)
                    }
                }
            }
            .padding()
        }
        .searchable(text: $searchText, prompt: "Search manifold content...")
        .navigationTitle("H-LSM Memory")
    }
}
