import SwiftUI

struct SoulView: View {
    @State private var tone = 0.5
    @State private var empathy = 0.5
    @State private var assertiveness = 0.5
    @State private var creativity = 0.5
    @State private var voiceProfile = "am_adam"
    
    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                VStack(alignment: .leading, spacing: 16) {
                    Text("Core Parameters").font(.headline).foregroundColor(.secondary)
                    VStack(alignment: .leading) {
                        Text("Tone (Casual ↔ Formal)")
                        Slider(value: $tone, in: 0...1)
                    }
                    VStack(alignment: .leading) {
                        Text("Empathy (Validation weight)")
                        Slider(value: $empathy, in: 0...1)
                    }
                    VStack(alignment: .leading) {
                        Text("Assertiveness (Directive strength)")
                        Slider(value: $assertiveness, in: 0...1)
                    }
                    VStack(alignment: .leading) {
                        Text("Creativity (Divergence)")
                        Slider(value: $creativity, in: 0...1)
                    }
                }
                .padding()
                .background(Color(.secondarySystemGroupedBackground))
                .cornerRadius(12)
                
                VStack(alignment: .leading, spacing: 16) {
                    Text("Identity & Voice").font(.headline).foregroundColor(.secondary)
                    HStack {
                        Text("Voice Profile")
                        Spacer()
                        Picker("Voice Profile", selection: $voiceProfile) {
                            Text("am_adam (Masculine / Deep Work)").tag("am_adam")
                            Text("af_heart (Feminine / Peak Performance)").tag("af_heart")
                            Text("af_bella (Feminine / Ambient)").tag("af_bella")
                            Text("am_michael (Masculine / Assertive)").tag("am_michael")
                            Text("af_sky (Feminine / Calm)").tag("af_sky")
                        }
                    }
                    Divider()
                    HStack {
                        Text("Identity Core")
                        Spacer()
                        Text("Alluci Polytope").foregroundColor(.secondary)
                    }
                }
                .padding()
                .background(Color(.secondarySystemGroupedBackground))
                .cornerRadius(12)
                
                VStack(alignment: .leading, spacing: 16) {
                    Text("Cognition Elements").font(.headline).foregroundColor(.secondary)
                    HStack { Text("Frameworks"); Spacer(); Text("Circular Economy, BMC...").foregroundColor(.secondary) }
                    Divider()
                    HStack { Text("Mindsets"); Spacer(); Text("Growth, Sovereign").foregroundColor(.secondary) }
                    Divider()
                    HStack { Text("Methodologies"); Spacer(); Text("First Principles").foregroundColor(.secondary) }
                }
                .padding()
                .background(Color(.secondarySystemGroupedBackground))
                .cornerRadius(12)
                
                Button("Save Soul Profile") {}
                    .frame(maxWidth: .infinity)
                    .buttonStyle(.borderedProminent)
            }
            .padding()
        }
        .navigationTitle("Soul Preferences")
    }
}
