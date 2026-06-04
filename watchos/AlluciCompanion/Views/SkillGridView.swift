import SwiftUI

struct SkillGridView: View {
    @State private var skills = [
        (name: "Workspace Bridge", icon: "briefcase.fill", isEnabled: true),
        (name: "Messaging Manifold", icon: "bubble.left.and.bubble.right.fill", isEnabled: true),
        (name: "Circular Design Guide", icon: "arrow.3.trianglepath", isEnabled: false),
        (name: "Humane Technology", icon: "person.crop.circle.badge.checkmark", isEnabled: true),
        (name: "Human Centered Design", icon: "person.2.fill", isEnabled: false),
        (name: "Business Model Canvas", icon: "tablecells.fill", isEnabled: true),
        (name: "Value Based Pricing", icon: "dollarsign.circle.fill", isEnabled: true),
        (name: "Price The Client", icon: "scalemass.fill", isEnabled: false),
        (name: "Verus Developer", icon: "link.circle.fill", isEnabled: true),
        (name: "Auth Registration", icon: "key.fill", isEnabled: true)
    ]
    
    let columns = [
        GridItem(.flexible()),
        GridItem(.flexible())
    ]
    
    var body: some View {
        ScrollView {
            LazyVGrid(columns: columns, spacing: 16) {
                ForEach(0..<skills.count, id: \.self) { index in
                    let skill = skills[index]
                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Image(systemName: skill.icon)
                                .font(.title2)
                                .foregroundColor(skill.isEnabled ? .accentColor : .gray)
                            Spacer()
                            Toggle("", isOn: $skills[index].isEnabled)
                                .labelsHidden()
                        }
                        
                        Text(skill.name)
                            .font(.headline)
                            .foregroundColor(.primary)
                            .lineLimit(2)
                            .minimumScaleFactor(0.8)
                        
                        Text(skill.isEnabled ? "Active" : "Suspended")
                            .font(.caption)
                            .foregroundColor(skill.isEnabled ? .green : .secondary)
                    }
                    .padding()
                    .background(Color(UIColor.secondarySystemBackground))
                    .cornerRadius(16)
                    .overlay(
                        RoundedRectangle(cornerRadius: 16)
                            .stroke(skill.isEnabled ? Color.accentColor.opacity(0.3) : Color.clear, lineWidth: 1)
                    )
                }
            }
            .padding()
        }
    }
}
