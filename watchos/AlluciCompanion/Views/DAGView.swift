import SwiftUI

struct DAGView: View {
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                DAGNode(title: "Web Scraper", status: "Completed", icon: "globe", isLast: false)
                DAGNode(title: "Text Summarizer", status: "Running", icon: "doc.text", isLast: false)
                DAGNode(title: "Sentiment Analysis", status: "Pending", icon: "brain", isLast: false)
                DAGNode(title: "Database Insert", status: "Pending", icon: "server.rack", isLast: true)
            }
            .padding()
        }
        .navigationTitle("DAG Timeline")
    }
}

struct DAGNode: View {
    let title: String
    let status: String
    let icon: String
    let isLast: Bool
    
    var body: some View {
        HStack(alignment: .top) {
            VStack {
                Image(systemName: icon)
                    .padding()
                    .background(status == "Completed" ? Color.green.opacity(0.2) : (status == "Running" ? Color.blue.opacity(0.2) : Color.gray.opacity(0.2)))
                    .foregroundColor(status == "Completed" ? .green : (status == "Running" ? .blue : .gray))
                    .clipShape(Circle())
                
                if !isLast {
                    Rectangle()
                        .fill(Color.gray.opacity(0.3))
                        .frame(width: 2, height: 40)
                }
            }
            
            VStack(alignment: .leading) {
                Text(title).font(.headline)
                Text(status)
                    .font(.caption)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(status == "Running" ? Color.blue : Color.gray)
                    .foregroundColor(.white)
                    .cornerRadius(8)
            }
            .padding(.top, 12)
            .padding(.leading, 8)
            
            Spacer()
        }
    }
}
