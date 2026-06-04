import SwiftUI

struct AgentTerminalView: View {
    @StateObject private var voiceManager = VoiceManager()
    @State private var inputText = ""
    @State private var messages = [
        (content: "System initialized. How can I assist?", isUser: false, id: "m1")
    ]
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        ForEach(messages, id: \.id) { msg in
                            HStack {
                                if msg.isUser { Spacer() }
                                Text(msg.content)
                                    .padding()
                                    .background(msg.isUser ? Color.accentColor : Color(.secondarySystemGroupedBackground))
                                    .foregroundColor(msg.isUser ? .white : .primary)
                                    .cornerRadius(16)
                                if !msg.isUser { Spacer() }
                            }
                            .padding(.horizontal)
                        }
                    }
                    .padding(.vertical)
                }
                
                Divider()
                
                HStack {
                    Button(action: {
                        if !voiceManager.isAuthorized {
                            voiceManager.requestAuthorization()
                        } else {
                            voiceManager.toggleRecording()
                        }
                    }) {
                        Image(systemName: voiceManager.isRecording ? "mic.fill" : "mic")
                            .font(.system(size: 24))
                            .foregroundColor(voiceManager.isRecording ? .red : .accentColor)
                            .scaleEffect(voiceManager.isRecording ? 1.2 : 1.0)
                            .animation(.easeInOut(duration: 0.3).repeatForever(autoreverses: true), value: voiceManager.isRecording)
                    }
                    .padding(.trailing, 8)
                    
                    TextField("Enter directive...", text: $inputText)
                        .textFieldStyle(RoundedBorderTextFieldStyle())
                        .onChange(of: voiceManager.transcribedText) { newValue in
                            if voiceManager.isRecording && !newValue.isEmpty {
                                inputText = newValue
                            }
                        }
                    
                    Button("Send") {
                        if !inputText.isEmpty {
                            let textToSend = inputText
                            messages.append((content: textToSend, isUser: true, id: UUID().uuidString))
                            inputText = ""
                            if voiceManager.isRecording {
                                voiceManager.toggleRecording() // Stop recording on send
                            }
                            
                            // Send to Context Router
                            let router = ContextRouter()
                            // Mocking the desktop state for the UI demo based on a local toggle or just assume false
                            // In real app, router is an EnvironmentObject or singleton updated by BLE
                            router.isDesktopInRange = false 
                            
                            router.routePrompt(textToSend) { response in
                                messages.append((content: response, isUser: false, id: UUID().uuidString))
                                voiceManager.speak(text: response)
                            }
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .padding(.leading, 8)
                }
                .padding()
                .background(Color(.systemBackground))
            }
            .navigationTitle("Alluci Agent")
            .onAppear {
                voiceManager.requestAuthorization()
            }
        }
    }
}
