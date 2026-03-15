import { create } from 'zustand';
import {
    Connection,
    SkillManifest,
    AuditEntry,
    ApiManifoldKeys,
    SoulManifest,
    Message
} from '../types';

export type ActiveView =
    | 'chat' | 'soul' | 'skills' | 'bridges' | 'memory'
    | 'api' | 'tasks' | 'files' | 'audit' | 'canvas'
    | 'sessions' | 'analytics' | 'crons'
    | 'agents' | 'config' | 'logs' | 'debug' | 'wallet' | 'node' | 'dag' | 'pvt';
export type Theme = 'light' | 'dark';

export interface AppState {
    // Connection & System Status
    isConnected: boolean;
    daemonStatus: 'ONLINE' | 'OFFLINE';
    harmonicStatus: string;
    isCameraActive: boolean;
    setIsConnected: (val: boolean) => void;
    setDaemonStatus: (val: 'ONLINE' | 'OFFLINE') => void;
    setHarmonicStatus: (val: string) => void;
    setIsCameraActive: (val: boolean) => void;
    accessToken: string | null;
    setAccessToken: (val: string | null) => void;
    needsOnboarding: boolean;
    setNeedsOnboarding: (val: boolean) => void;
    updateAvailable: boolean;
    setUpdateAvailable: (val: boolean) => void;
    latestVersion: string | null;
    setLatestVersion: (val: string | null) => void;

    // Navigation — single activeView replaces 9 modal booleans
    activeView: ActiveView;
    setActiveView: (val: ActiveView) => void;

    // Theme
    theme: Theme;
    setTheme: (val: Theme) => void;
    toggleTheme: () => void;

    // Sidebar
    isSidebarCollapsed: boolean;
    setSidebarCollapsed: (val: boolean) => void;

    // Affective Engine widget
    isAceExpanded: boolean;
    setAceExpanded: (val: boolean) => void;

    // Mobile
    mobileView: 'terminal' | 'vision' | 'system';
    isMobileMenuOpen: boolean;
    setMobileView: (val: 'terminal' | 'vision' | 'system') => void;
    setIsMobileMenuOpen: (val: boolean) => void;

    // Sub-modals (wizard overlays that sit ON TOP of a view)
    showSkillWizard: boolean;
    setShowSkillWizard: (val: boolean) => void;

    // API & Security
    apiKeys: ApiManifoldKeys;
    setApiKeys: (val: ApiManifoldKeys | ((prev: ApiManifoldKeys) => ApiManifoldKeys)) => void;

    // Data Collections
    connections: Connection[];
    setConnections: (val: Connection[] | ((prev: Connection[]) => Connection[])) => void;
    skills: SkillManifest[];
    setSkills: (val: SkillManifest[] | ((prev: SkillManifest[]) => SkillManifest[])) => void;
    auditLog: AuditEntry[];
    setAuditLog: (val: AuditEntry[] | ((prev: AuditEntry[]) => AuditEntry[])) => void;

    // Biometrics (User)
    biometrics: {
        emotional: number;
        physical: number;
        cognitive: number;
        hr: number;
        hrv: number;
        respiratoryRate: number;
        sleepEfficiency: number;
    };
    updateBiometrics: (updates: Partial<AppState['biometrics']>) => void;

    // Agent State
    agent: {
        emotional: number;
        physical: number;
        cognitive: number;
        valenceCurvature: number;
        manifoldIntegrity: number;
    };
    updateAgent: (updates: Partial<AppState['agent']> | ((prev: AppState['agent']) => Partial<AppState['agent']>)) => void;

    // ACE & Canvas
    activeNudges: any[];
    canvasNodes: any[];
    setActiveNudges: (fn: (prev: any[]) => any[]) => void;
    setCanvasNodes: (fn: (prev: any[]) => any[]) => void;

    // External Events
    cloudFiles: any[];
    socialEvents: any[];
    enterpriseEvents: any[];
    setCloudFiles: (val: any[] | ((prev: any[]) => any[])) => void;
    setSocialEvents: (val: any[] | ((prev: any[]) => any[])) => void;
    setEnterpriseEvents: (val: any[] | ((prev: any[]) => any[])) => void;

    // Manifests
    baseManifest: SoulManifest | null;
    setBaseManifest: (val: SoulManifest | null) => void;

    // Interaction
    transcriptions: Message[];
    isProcessing: boolean;
    setTranscriptions: (fn: (prev: Message[]) => Message[]) => void;
    setIsProcessing: (val: boolean) => void;
    isVoiceRecording: boolean;
    setIsVoiceRecording: (val: boolean) => void;
    voiceTranscription: string | null;
    setVoiceTranscription: (val: string | null) => void;
    textInput: string;
    setTextInput: (val: string | ((prev: string) => string)) => void;

    // Sprint 3: Exec Approval
    pendingApproval: {
        request_id: string;
        command: string;
        tool_name: string;
        context: string;
    } | null;
    setPendingApproval: (val: AppState['pendingApproval']) => void;

    // Sprint A: Focus Mode & Abort
    focusMode: boolean;
    setFocusMode: (val: boolean) => void;
    modelFallbackMessage: string | null;
    setModelFallbackMessage: (val: string | null) => void;

    // Sprint B: Sessions
    sessions: any[];
    activeSessionKey: string;
    setSessions: (val: AppState['sessions']) => void;
    setActiveSessionKey: (val: string) => void;

    // Sprint H: Presence
    presenceCount: number;
    sessionCount: number;
    setPresenceCount: (val: number) => void;
    setSessionCount: (val: number) => void;

    // Presence Data
    presence: { instances: number; sessions: number };
    setPresence: (val: Partial<AppState['presence']>) => void;

    // Verus Wallet State
    walletMode: 'lite' | 'sovereign';
    setWalletMode: (val: 'lite' | 'sovereign') => void;
    walletStatus: 'synced' | 'syncing' | 'offline';
    setWalletStatus: (val: 'synced' | 'syncing' | 'offline') => void;

    // DAG Planner
    activeRunId: number | null;
    setActiveRunId: (id: number | null) => void;

    // PVT Health Dashboard
    pvtHealth: {
        P: number; V: number; T: number;
        psi: number; coherence: number;
        status: string; isRuptured: boolean;
        phi_total: number;
    };
    setPvtHealth: (val: Partial<AppState['pvtHealth']>) => void;
    
    // Hydration
    hydrate: () => Promise<void>;
}

export const useStore = create<AppState>((set) => ({
    // Connection & System Status
    isConnected: false,
    daemonStatus: 'OFFLINE',
    harmonicStatus: 'Inactive',
    isCameraActive: false,
    setIsConnected: (val) => set({ isConnected: val }),
    setDaemonStatus: (val) => set({ daemonStatus: val }),
    setHarmonicStatus: (val) => set({ harmonicStatus: val }),
    setIsCameraActive: (val) => set({ isCameraActive: val }),
    accessToken: null,
    setAccessToken: (val) => set({ accessToken: val }),
    needsOnboarding: false,
    setNeedsOnboarding: (val) => set({ needsOnboarding: val }),
    updateAvailable: false,
    setUpdateAvailable: (val) => set({ updateAvailable: val }),
    latestVersion: null,
    setLatestVersion: (val) => set({ latestVersion: val }),

    // Navigation
    activeView: 'chat',
    setActiveView: (val) => set({ activeView: val }),

    // Theme
    theme: (localStorage.getItem('alluci_theme') as Theme) || 'dark',
    setTheme: (val) => {
        localStorage.setItem('alluci_theme', val);
        document.documentElement.setAttribute('data-theme', val);
        set({ theme: val });
    },
    toggleTheme: () => set((state) => {
        const next = state.theme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('alluci_theme', next);
        document.documentElement.setAttribute('data-theme', next);
        return { theme: next };
    }),

    // Sidebar
    isSidebarCollapsed: false,
    setSidebarCollapsed: (val) => set({ isSidebarCollapsed: val }),

    // ACE Widget
    isAceExpanded: false,
    setAceExpanded: (val) => set({ isAceExpanded: val }),

    // Mobile
    mobileView: 'terminal',
    isMobileMenuOpen: false,
    setMobileView: (val) => set({ mobileView: val }),
    setIsMobileMenuOpen: (val) => set({ isMobileMenuOpen: val }),

    // Sub-modals
    showSkillWizard: false,
    setShowSkillWizard: (val) => set({ showSkillWizard: val }),

    // API & Security
    apiKeys: {
        llm: { openai: '', anthropic: '', googleCloud: '', groq: '', deepseek: '' },
        audio: { openaiRealtime: '', elevenLabsAgents: '', retellAi: '', inworldAi: '' },
        music: { suno: '', elevenLabsMusic: '', stableAudio: '', soundverse: '', udio: '', googleLyria: '' },
        image: { openaiDalle: '', falAi: '', midjourney: '', adobeFirefly: '', googleNanoBanana: '', seedance: '' },
        video: { runway: '', luma: '', heygen: '', livepeer: '', googleVeo: '', googleGenie: '' }
    },
    setApiKeys: (val) => set((state) => ({
        apiKeys: typeof val === 'function' ? val(state.apiKeys) : val
    })),

    // Data Collections
    connections: [],
    setConnections: (val) => set((state) => ({
        connections: typeof val === 'function' ? val(state.connections) : val
    })),
    skills: [],
    setSkills: (val) => set((state) => ({
        skills: typeof val === 'function' ? val(state.skills) : val
    })),
    auditLog: [],
    setAuditLog: (val) => set((state) => ({
        auditLog: typeof val === 'function' ? val(state.auditLog) : val
    })),

    // Biometrics
    biometrics: {
        emotional: 0.4,
        physical: 0.3,
        cognitive: 0.6,
        hr: 72,
        hrv: 55,
        respiratoryRate: 14,
        sleepEfficiency: 0.85
    },
    updateBiometrics: (updates) => set((state) => ({
        biometrics: { ...state.biometrics, ...updates }
    })),

    // Agent State
    agent: {
        emotional: 0.2,
        physical: 0.5,
        cognitive: 0.9,
        valenceCurvature: 0.3,
        manifoldIntegrity: 0.12
    },
    updateAgent: (val) => set((state) => ({
        agent: { ...state.agent, ...(typeof val === 'function' ? val(state.agent) : val) }
    })),

    // ACE & Canvas
    activeNudges: [],
    canvasNodes: [{ id: 'initial_node', type: 'TEXT', content: 'SYSTEM READY: A2UI_PROTOCOL_ACTIVE', x: 50, y: 150 }],
    setActiveNudges: (fn) => set((state) => ({ activeNudges: fn(state.activeNudges) })),
    setCanvasNodes: (fn) => set((state) => ({ canvasNodes: fn(state.canvasNodes) })),

    // External Events
    cloudFiles: [],
    socialEvents: [],
    enterpriseEvents: [],
    setCloudFiles: (val) => set((state) => ({
        cloudFiles: typeof val === 'function' ? val(state.cloudFiles) : val
    })),
    setSocialEvents: (val) => set((state) => ({
        socialEvents: typeof val === 'function' ? val(state.socialEvents) : val
    })),
    setEnterpriseEvents: (val) => set((state) => ({
        enterpriseEvents: typeof val === 'function' ? val(state.enterpriseEvents) : val
    })),

    // Manifests
    baseManifest: null,
    setBaseManifest: (val) => set({ baseManifest: val }),

    // Interaction
    transcriptions: [],
    isProcessing: false,
    setTranscriptions: (fn) => set((state) => ({ transcriptions: fn(state.transcriptions) })),
    setIsProcessing: (val) => set({ isProcessing: val }),
    isVoiceRecording: false,
    setIsVoiceRecording: (val) => set({ isVoiceRecording: val }),
    voiceTranscription: null,
    setVoiceTranscription: (val) => set({ voiceTranscription: val }),
    textInput: "",
    setTextInput: (val) => set((state) => ({
        textInput: typeof val === 'function' ? val(state.textInput) : val
    })),

    // Sprint 3: Exec Approval
    pendingApproval: null,
    setPendingApproval: (val) => set({ pendingApproval: val }),

    // Sprint A: Focus Mode & Abort
    focusMode: false,
    setFocusMode: (val) => set({ focusMode: val }),
    modelFallbackMessage: null,
    setModelFallbackMessage: (val) => set({ modelFallbackMessage: val }),

    // Sprint B: Sessions
    sessions: [],
    activeSessionKey: '',
    setSessions: (val) => set({ sessions: val }),
    setActiveSessionKey: (val) => set({ activeSessionKey: val }),

    // Sprint H: Presence
    presenceCount: 0,
    sessionCount: 0,
    setPresenceCount: (val) => set({ presenceCount: val }),
    setSessionCount: (val) => set({ sessionCount: val }),

    presence: { instances: 0, sessions: 0 },
    setPresence: (val) => set((state) => ({ presence: { ...state.presence, ...val } })),

    // Verus Wallet Initial State
    walletMode: 'lite',
    setWalletMode: (val) => set({ walletMode: val }),
    walletStatus: 'offline',
    setWalletStatus: (val) => set({ walletStatus: val }),

    // DAG Planner
    activeRunId: null,
    setActiveRunId: (id) => set({ activeRunId: id }),

    // PVT Health Dashboard
    pvtHealth: {
        P: 0.0, V: 1.0, T: 0.0,
        psi: 0.0, coherence: 1.0,
        status: 'HEALTHY', isRuptured: false,
        phi_total: 0
    },
    setPvtHealth: (val) => set((state) => ({
        pvtHealth: { ...state.pvtHealth, ...val }
    })),
    hydrate: async () => {
        const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';
        // Only attempt hydration if the session signal cookie exists
        if (!document.cookie.includes('alluci_session=1')) return;
        
        try {
            const res = await fetch(`${DAEMON_URL}/api/session`, { credentials: 'include' });
            if (res.ok) {
                const data = await res.json();
                if (data.status === 'SUCCESS') {
                    set({
                        isConnected: true,
                        baseManifest: data.soul,
                        connections: data.connections
                    });
                }
            }
        } catch (e) {
            console.warn("[ HYDRATE ]: Failed to restore session", e);
        }
    },
}));
