import SwiftUI
import LocalAuthentication
import AuthenticationServices

struct SkillApprovalsView: View {
    @State private var isAuthenticated = false
    
    var body: some View {
        NavigationStack {
            ScrollView {
                if !isAuthenticated {
                    VStack(spacing: 16) {
                        Image(systemName: "lock.shield.fill")
                            .font(.system(size: 48))
                            .foregroundColor(.orange)
                        
                        Text("Security Approvals Require Authentication")
                            .multilineTextAlignment(.center)
                            .font(.headline)
                        
                        Button("Authenticate with FaceID / TouchID") {
                            authenticateUser()
                        }
                        .buttonStyle(.borderedProminent)
                        
                        Text("or")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                        
                        Button("Use Passkey") {
                            authenticateWithPasskey()
                        }
                        .buttonStyle(.bordered)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 40)
                } else {
                    VStack(alignment: .leading, spacing: 16) {
                        Text("Pending Agent Requests")
                            .font(.headline)
                            .foregroundColor(.secondary)
                        
                        VStack(alignment: .leading, spacing: 8) {
                            HStack {
                                Image(systemName: "exclamationmark.triangle.fill")
                                    .foregroundColor(.orange)
                                Text("High Privilege Action")
                                    .font(.subheadline)
                                    .fontWeight(.bold)
                            }
                            Text("Agent requested access to modify root configuration files in `polytope_data.kuzu` (Cognitive Plane).")
                                .font(.caption)
                            
                            HStack {
                                Button("Deny") {}
                                    .buttonStyle(.bordered)
                                    .tint(.red)
                                Spacer()
                                Button("Approve") {}
                                    .buttonStyle(.borderedProminent)
                                    .tint(.green)
                            }
                            .padding(.top, 4)
                        }
                        .padding()
                        .background(Color(.secondarySystemGroupedBackground))
                        .cornerRadius(12)
                    }
                    .padding()
                }
            }
            .navigationTitle("Skill Approvals")
        }
    }
    
    private func authenticateUser() {
        let context = LAContext()
        var error: NSError?
        
        if context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) {
            context.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, localizedReason: "Authenticate to view sensitive agent actions") { success, error in
                DispatchQueue.main.async {
                    if success {
                        self.isAuthenticated = true
                    }
                }
            }
        } else {
            // Fallback for Simulator
            self.isAuthenticated = true
        }
    }
    
    private func authenticateWithPasskey() {
        // Prepare the Passkey challenge (Normally fetched from the backend)
        let challenge = "desktop_daemon_auth_challenge".data(using: .utf8)!
        let provider = ASAuthorizationPlatformPublicKeyCredentialProvider(relyingPartyIdentifier: "ai.alluci.companion")
        let request = provider.createCredentialAssertionRequest(challenge: challenge)
        
        let controller = ASAuthorizationController(authorizationRequests: [request])
        // Normally you would set a delegate here to handle the assertion response:
        // controller.delegate = self
        // controller.presentationContextProvider = self
        controller.performRequests()
        
        // For Simulator/Demo purposes:
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            self.isAuthenticated = true
        }
    }
}
