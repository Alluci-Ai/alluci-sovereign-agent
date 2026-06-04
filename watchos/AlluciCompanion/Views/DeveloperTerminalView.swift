import SwiftUI

struct DeveloperTerminalView: View {
    @State private var commandInput = ""
    @State private var outputLog = [
        "[2026-06-03 15:42:11] INITIALIZING TCP SOCKET...",
        "[2026-06-03 15:42:12] SUCCESS: Bound to port 8000.",
        "[2026-06-03 15:43:00] ACE Engine daemon synchronized.",
        "[2026-06-03 15:45:10] AWAITING RPC COMMANDS."
    ]
    
    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 4) {
                    ForEach(outputLog, id: \.self) { line in
                        Text(line)
                            .font(.system(size: 11, design: .monospaced))
                            .foregroundColor(.green)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .padding()
            }
            .background(Color.black)
            
            HStack {
                Text(">_").font(.system(.subheadline, design: .monospaced)).foregroundColor(.green)
                TextField("Execute RPC Command...", text: $commandInput)
                    .font(.system(.subheadline, design: .monospaced))
                    .foregroundColor(.green)
                    .textFieldStyle(PlainTextFieldStyle())
                    .onSubmit {
                        if !commandInput.isEmpty {
                            outputLog.append("> \(commandInput)")
                            outputLog.append("ERR: Socket offline. Execution aborted.")
                            commandInput = ""
                        }
                    }
            }
            .padding()
            .background(Color(white: 0.1))
        }
        .navigationTitle("Developer Terminal")
        .navigationBarTitleDisplayMode(.inline)
    }
}
