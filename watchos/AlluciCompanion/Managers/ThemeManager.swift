import SwiftUI

struct AppThemeModifier: ViewModifier {
    @AppStorage("systemTheme") private var systemTheme: Int = 0 // 0 = System, 1 = Light, 2 = Dark
    
    func body(content: Content) -> some View {
        content
            .preferredColorScheme(systemTheme == 1 ? .light : (systemTheme == 2 ? .dark : nil))
    }
}

extension View {
    func applyAppTheme() -> some View {
        self.modifier(AppThemeModifier())
    }
}
