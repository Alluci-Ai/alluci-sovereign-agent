import SwiftUI
import BackgroundTasks

@main
struct AlluciCompanionApp: App {
    @StateObject var watchManager = WatchConnectivityManager()
    @StateObject var mdnsListener = MDNSListener()
    @StateObject var tcpServer = TCPSocketServer()
    
    var body: some Scene {
        WindowGroup {
            MainTabView()
                .environmentObject(watchManager)
                .environmentObject(tcpServer)
                .environmentObject(mdnsListener)
                .tint(.green)
                .applyAppTheme()
                .onAppear {
                    mdnsListener.startBroadcasting(port: 8124)
                    tcpServer.start(port: 8124)
                }
        }
        .backgroundTask(.appRefresh("ai.alluci.companion.refresh")) {
            await handleAppRefresh()
        }
    }
    
    func handleAppRefresh() async {
        print("Executing Background App Refresh...")
        let request = BGAppRefreshTaskRequest(identifier: "ai.alluci.companion.refresh")
        request.earliestBeginDate = Date(timeIntervalSinceNow: 15 * 60)
        try? BGTaskScheduler.shared.submit(request)
    }
}

struct MainTabView: View {
    var body: some View {
        TabView {
            ChatTabView()
                .tabItem {
                    Label("Chat", systemImage: "bubble.left.and.bubble.right.fill")
                }

            WorkforceTabView()
                .tabItem {
                    Label("Workforce", systemImage: "brain.head.profile")
                }
                
            OpsTabView()
                .tabItem {
                    Label("Ops", systemImage: "network")
                }
                
            DashboardView() // ACE Engine
                .tabItem {
                    Label("ACE Engine", systemImage: "waveform.path.ecg")
                }
            
            MoreTabView()
                .tabItem {
                    Label("More", systemImage: "ellipsis.circle")
                }
        }
    }
}

// Wrapper views for Navigation Stacks
struct ChatTabView: View {
    var body: some View {
        NavigationStack {
            AgentTerminalView() // Repurposed as Chat
        }
    }
}

struct WorkforceTabView: View {
    var body: some View {
        NavigationStack {
            AgentsView()
        }
    }
}

struct OpsTabView: View {
    var body: some View {
        NavigationStack {
            List {
                NavigationLink("Tasks", destination: TasksView())
                NavigationLink("DAG Planner", destination: DAGView())
                NavigationLink("Crons", destination: CronsView())
            }
            .navigationTitle("Operations")
        }
    }
}

struct MoreTabView: View {
    @AppStorage("systemTheme") private var systemTheme: Int = 0
    
    var body: some View {
        NavigationStack {
            List {
                Section(header: Text("Workforce Config")) {
                    NavigationLink("Skills Library", destination: SkillGridView())
                    NavigationLink("H-LSM Memory", destination: MemoryView())
                    NavigationLink("Soul Preferences", destination: SoulView())
                }
                
                Section(header: Text("Ecosystem & Identity")) {
                    NavigationLink("Sovereign Wallet", destination: WalletView())
                    NavigationLink("Bridges", destination: BridgeCenterView())
                    NavigationLink("Skill Approvals", destination: SkillApprovalsView())
                }
                
                Section(header: Text("System Operations")) {
                    NavigationLink("Developer Terminal", destination: DeveloperTerminalView())
                    NavigationLink("Usage Analytics", destination: UsageView())
                    NavigationLink("Active Sessions", destination: SessionsView())
                }
                
                Section(header: Text("Preferences")) {
                    Picker("Theme", selection: $systemTheme) {
                        Text("System").tag(0)
                        Text("Light").tag(1)
                        Text("Dark").tag(2)
                    }
                }
            }
            .navigationTitle("More")
        }
    }
}
