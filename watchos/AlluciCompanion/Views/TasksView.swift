import SwiftUI

struct TasksView: View {
    @State private var tasks = [
        (title: "Analyze Q3 Earnings Report", isCompleted: false),
        (title: "Update Local DNS Records", isCompleted: true),
        (title: "Draft email to investors", isCompleted: false)
    ]
    
    var body: some View {
        ScrollView {
            VStack(spacing: 12) {
                ForEach($tasks, id: \.title) { $task in
                    HStack {
                        Image(systemName: task.isCompleted ? "checkmark.circle.fill" : "circle")
                            .foregroundColor(task.isCompleted ? .green : .gray)
                            .onTapGesture {
                                task.isCompleted.toggle()
                            }
                        Text(task.title)
                            .strikethrough(task.isCompleted, color: .gray)
                            .foregroundColor(task.isCompleted ? .secondary : .primary)
                        Spacer()
                    }
                    .padding()
                    .background(Color(.secondarySystemGroupedBackground))
                    .cornerRadius(12)
                }
            }
            .padding()
        }
        .navigationTitle("Agent Tasks")
        .toolbar {
            EditButton()
        }
    }
}
