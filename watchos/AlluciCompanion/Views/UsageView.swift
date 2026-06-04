import SwiftUI
import Charts

struct UsageView: View {
    let data = [
        (day: "Mon", tokens: 12000),
        (day: "Tue", tokens: 15000),
        (day: "Wed", tokens: 9000),
        (day: "Thu", tokens: 22000),
        (day: "Fri", tokens: 18000)
    ]
    
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("Token Usage (7 Days)")
                    .font(.headline)
                    .padding(.horizontal)
                
                Chart {
                    ForEach(data, id: \.day) { item in
                        BarMark(
                            x: .value("Day", item.day),
                            y: .value("Tokens", item.tokens)
                        )
                        .foregroundStyle(Color.accentColor.gradient)
                    }
                }
                .frame(height: 300)
                .padding()
                
                VStack(spacing: 16) {
                    HStack {
                        Text("Total Cost Estimate")
                        Spacer()
                        Text("$4.20").bold()
                    }
                    Divider()
                    HStack {
                        Text("Average Inference Time")
                        Spacer()
                        Text("1.2s").bold()
                    }
                }
                .padding()
                .background(Color(.secondarySystemGroupedBackground))
                .cornerRadius(12)
                .padding(.horizontal)
            }
            .padding(.vertical)
        }
        .navigationTitle("Usage Analytics")
    }
}
