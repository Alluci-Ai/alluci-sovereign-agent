import React, { useState, useEffect, useRef, useCallback } from 'react';
import { AlluciGeminiService, decode, decodeAudioData } from './geminiService';
import { AlluciSovereignService } from './sovereignService';
import { SkillVerifier, AuditLedger, BioVault, SovereignSecurityManager, clamp01 } from './alluciCore';
import { BridgeManager } from './bridgeManager';
import { useStore } from './store/useStore';
import {
  Connection,
  SkillManifest,
  SoulManifest,
  ApiManifoldKeys
} from './types';
import { INITIAL_CONNECTIONS } from './components/constants';

// Layout Components
import SystemHeader from './features/system/SystemHeader';
import Sidebar from './components/Sidebar';
import { ErrorBoundary } from './components/ErrorBoundary';

// Content Views
import TerminalView from './features/terminal/TerminalView';
import CommandBar from './features/terminal/CommandBar';
import AuditChainPanel from './features/system/AuditChainPanel';
import LiveCanvas from './components/LiveCanvas';
import { MobileNav, MobileMenu } from './components/Visualizers';

// Inline Panels (rendered in main content area)
import SoulPreferencesPanel from './components/SoulPreferencesPanel';
import SkillBuilderWizard from './components/SkillBuilderWizard';
import ApiWizard from './components/ApiWizard';
import { TaskPanel } from './components/TaskPanel';
import { AuthPortal } from './components/AuthPortal';
import BridgeCenter from './components/BridgeCenter';
import { SkillGrid, SkillDetailOverlay } from './components/SkillGrid';

// Hooks
import { useDaemonStatus } from './hooks/useDaemonStatus';
import { useBiometrics } from './hooks/useBiometrics';
import { useIdentityAuth } from './hooks/useIdentity';
import { useSoulAdaptation } from './hooks/useSoulAdaptation';
import { useSovereignConnection } from './hooks/useConnection';
import { useBridges } from './hooks/useBridges';
import { useInteractions } from './hooks/useInteractions';

// Admin & Sprint 3
import { adminService } from './adminService';
import { ExecApprovalModal } from './components/ExecApprovalModal';
import { OnboardingWizard } from './features/onboarding/OnboardingWizard';
import { RpcConsole } from './features/system/RpcConsole';

// Sprint A–H New Panels
import { AbortButton } from './features/chat/AbortButton';
import { ModelFallbackBanner } from './features/chat/ModelFallbackBanner';
import { SessionsPanel } from './features/sessions/SessionsPanel';
import { AnalyticsPanel } from './features/analytics/AnalyticsPanel';
import { ConfigPanel } from './features/config/ConfigPanel';
import { LogPanel } from './features/observability/LogPanel';
import { AgentsPanel } from './features/agents/AgentsPanel';
import { DebugPanel } from './features/debug/DebugPanel';
import CronPanel from './features/scheduling/CronPanel';
import { WalletPanel } from './features/wallet/WalletPanel';
import { NodePanel } from './features/wallet/NodePanel';
import { MemoryPanel } from './features/memory/MemoryPanel';
import { DAGPanel } from './features/dag/DAGPanel';
import PVTDashboard from './features/observability/PVTDashboard';
import { useTranslation } from 'react-i18next';
import './styles/dag.css';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

const App: React.FC = () => {
  const {
    isConnected, setIsConnected,
    daemonStatus, setDaemonStatus,
    harmonicStatus, setHarmonicStatus,
    isCameraActive, setIsCameraActive,
    isMobileMenuOpen, setIsMobileMenuOpen,
    activeView, setActiveView,
    isSidebarCollapsed,
    showSkillWizard, setShowSkillWizard,
    apiKeys, setApiKeys,
    connections, setConnections,
    skills, setSkills,
    auditLog, setAuditLog,
    biometrics, updateBiometrics,
    agent, updateAgent,
    activeNudges, setActiveNudges,
    canvasNodes, setCanvasNodes,
    cloudFiles, setCloudFiles,
    socialEvents, setSocialEvents,
    enterpriseEvents, setEnterpriseEvents,
    baseManifest, setBaseManifest,
    transcriptions, setTranscriptions,
    isProcessing, setIsProcessing,
    accessToken,
    pendingApproval,
    setPendingApproval,
    focusMode,
    modelFallbackMessage, setModelFallbackMessage,
    updateAvailable,
    latestVersion,
    needsOnboarding,
    hydrate
  } = useStore();

  // Core Refs
  const geminiServiceRef = useRef<AlluciGeminiService | null>(null);
  const sovereignServiceRef = useRef<AlluciSovereignService | null>(null);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (bridgeManagerRef.current) {
      bridgeManagerRef.current.setAccessToken(accessToken);
    }
  }, [accessToken]);

  // ── Admin WebSocket Connection (Sprint 3) ──────────────────────────────────
  useEffect(() => {
    if (accessToken) {
      adminService.connect(accessToken, {
        onApprovalRequest: (req) => {
          console.info("[ ADMIN ]: Exec Approval Required!", req);
          setPendingApproval(req);
        },
        onSystemEvent: (method, params) => {
          console.log(`[ ADMIN EVENT ]: ${method}`, params);
          if (method === 'system.heartbeat') {
            useStore.getState().setPresence({
              instances: params.instances || 0,
              sessions: params.sessions || 0
            });
          } else if (method === 'usage.alert') {
            setActiveNudges(prev => [...prev, { id: `usage_${Date.now()}`, message: `Usage Alert: ${params.reason}` }]);
          } else if (method === 'model.fallback') {
            setModelFallbackMessage(`⚠ Primary model unavailable. Using ${params.fallback_model}`);
          } else if (method === 'compaction.status') {
            // Append Context Compaction entry 
            setTranscriptions(prev => [...prev, {
              text: '',
              isUser: false,
              isCompaction: true,
              tokenCount: params.tokenCount,
              timestamp: new Date().toISOString()
            }]);
          } else if (method === 'manifold.pvt') {
            // PVT Health Dashboard real-time update
            useStore.getState().setPvtHealth({
              P: params.P ?? 0,
              V: params.V ?? 1,
              T: params.T ?? 0,
              psi: params.psi ?? 0,
              coherence: params.coherence ?? 1,
              status: params.status ?? 'HEALTHY',
              isRuptured: params.is_ruptured ?? false,
              phi_total: params.phi_total ?? 0
            });
          } else if (method === 'manifold.rupture') {
            useStore.getState().setPvtHealth({ isRuptured: true });
          }
        },
        onOpen: () => setIsConnected(true),
        onClose: () => setIsConnected(false)
      });
    }
    return () => adminService.disconnect();
  }, [accessToken, setPendingApproval, setIsConnected, setActiveNudges]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const nextStartTimeRef = useRef<number>(0);
  const sourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const frameIntervalRef = useRef<number | null>(null);
  const auditLedgerRef = useRef(new AuditLedger(DAEMON_URL));
  const securityManagerRef = useRef(new SovereignSecurityManager(auditLedgerRef.current));
  const bridgeManagerRef = useRef(new BridgeManager(securityManagerRef.current));
  const skillVerifier = useRef(new SkillVerifier());

  // Local States
  const [activeAuth, setActiveAuth] = useState<Connection | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<SkillManifest | null>(null);
  const [sovereignMode, setSovereignMode] = useState(true);
  const [audioStream, setAudioStream] = useState<MediaStream | null>(null);

  // Hooks
  useDaemonStatus();
  useBiometrics();
  const { authStatus, handleDaemonLogin } = useIdentityAuth();
  useSoulAdaptation(geminiServiceRef.current);

  const refreshAuditLog = useCallback(() => {
    if (geminiServiceRef.current) setAuditLog(geminiServiceRef.current.audit.getEntries());
  }, [setAuditLog]);

  const handleAudioOutput = useCallback(async (base64Audio: string) => {
    if (!audioContextRef.current) return;
    const ctx = audioContextRef.current;
    nextStartTimeRef.current = Math.max(nextStartTimeRef.current, ctx.currentTime);
    const buffer = await decodeAudioData(decode(base64Audio), ctx, 24000, 1);
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.start(nextStartTimeRef.current);
    nextStartTimeRef.current += buffer.duration;
    sourcesRef.current.add(source);
    updateAgent(prev => ({ ...prev, valenceCurvature: clamp01(prev.valenceCurvature + 0.15) }));
  }, [updateAgent]);

  const handleSystemUpdate = useCallback(() => {
    if (window.confirm(`Initiate daemon update to v${latestVersion}? System will reboot.`)) {
      adminService.sendRPC('system.update', {});
    }
  }, [latestVersion]);

  const [artifactWidth, setArtifactWidth] = useState(parseInt(localStorage.getItem('alluci_artifact_width') || '400'));
  const [isResizing, setIsResizing] = useState(false);

  const startResizing = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  useEffect(() => {
    if (!isResizing) return;
    const handleMouseMove = (e: MouseEvent) => {
      const newWidth = window.innerWidth - e.clientX;
      if (newWidth > 320 && newWidth < 800) {
        setArtifactWidth(newWidth);
      }
    };
    const handleMouseUp = () => {
      setIsResizing(false);
      localStorage.setItem('alluci_artifact_width', artifactWidth.toString());
    };
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, artifactWidth]);

  const { handleConnect } = useSovereignConnection(
    geminiServiceRef,
    sovereignServiceRef,
    audioContextRef,
    sourcesRef,
    nextStartTimeRef,
    refreshAuditLog,
    handleAudioOutput,
    sovereignMode,
    setAudioStream
  );

  const {
    handleRotateKeys,
    handleFlushCache,
    handleSaveApiKeys,
    handleSocialAction,
    handleEnterpriseAction,
    handlePulse
  } = useBridges(bridgeManagerRef, securityManagerRef, auditLedgerRef, refreshAuditLog);

  const {
    textInput, setTextInput,
    attachments, setAttachments,
    handleCommandSubmit,
    handleFileChange,
    handlePaste,
    removeAttachment,
    abortControllerRef,
  } = useInteractions(geminiServiceRef, isConnected, handleAudioOutput, refreshAuditLog, fileInputRef);

  // Ripple effect
  useEffect(() => {
    const handleRipple = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const rippleElement = target.closest('.glass-btn, .sidebar__item') as HTMLElement | null;
      if (!rippleElement) return;

      const rect = rippleElement.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const ripple = document.createElement('span');
      ripple.className = 'glass-ripple';
      ripple.style.left = `${x}px`;
      ripple.style.top = `${y}px`;

      rippleElement.style.overflow = 'hidden';
      rippleElement.appendChild(ripple);

      setTimeout(() => { ripple.remove(); }, 600);
    };

    document.addEventListener('click', handleRipple);
    return () => document.removeEventListener('click', handleRipple);
  }, []);

  const saveApiKeysToDaemon = async (keys: ApiManifoldKeys) => {
    try {
      const res = await fetch(`${DAEMON_URL}/api/v1/vault/keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(keys),
        credentials: 'include'
      });
      if (res.ok) {
        setApiKeys(keys);
      } else {
        console.error("Failed to save keys:", await res.text());
      }
    } catch (e) {
      console.error("Failed to save keys", e);
    }
  };

  useEffect(() => {
    audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
    geminiServiceRef.current = new AlluciGeminiService();

    const loadInitialData = async () => {
      try {
        const res = await fetch(`${DAEMON_URL}/api/v1/vault/keys`, { credentials: 'include' });
        if (res.ok) {
          const keys = await res.json();
          if (keys && Object.keys(keys).length > 0) setApiKeys(keys);
        }
        const soulRes = await fetch(`${DAEMON_URL}/api/v1/soul/manifest`, { credentials: 'include' });
        if (soulRes.ok) {
          const manifest = await soulRes.json();
          if (manifest) {
            geminiServiceRef.current?.setPersonality(manifest);
            setBaseManifest(manifest);
          }
        }
      } catch (e) { }
    };
    loadInitialData();

    if (connections.length === 0) setConnections(INITIAL_CONNECTIONS);

    return () => {
      geminiServiceRef.current?.disconnect();
      if (frameIntervalRef.current) clearInterval(frameIntervalRef.current);
    };
  }, []);

  const fetchSkills = useCallback(async () => {
    const core = skillVerifier.current.getManifests();
    try {
      const res = await fetch(`${DAEMON_URL}/api/v1/skills`, { credentials: 'include' });
      if (res.ok) {
        const custom = await res.json();
        const combined = [...core];
        custom.forEach((c: SkillManifest) => {
          if (!combined.find(k => k.id === c.id)) combined.push(c);
        });
        setSkills(combined);
        return;
      }
    } catch (e) { }
    setSkills(core);
  }, [setSkills]);

  useEffect(() => { fetchSkills(); }, [fetchSkills]);

  const toggleCamera = async () => {
    if (isCameraActive) {
      setIsCameraActive(false);
      (videoRef.current?.srcObject as MediaStream)?.getTracks().forEach(t => t.stop());
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setIsCameraActive(true);
        frameIntervalRef.current = window.setInterval(() => {
          if (canvasRef.current && isConnected) {
            const ctx = canvasRef.current.getContext('2d');
            ctx?.drawImage(videoRef.current!, 0, 0, 320, 240);
            geminiServiceRef.current?.sendVideoFrame(canvasRef.current.toDataURL('image/jpeg', 0.5).split(',')[1]);
          }
        }, 1500);
      }
    } catch (err) { console.error(err); }
  };

  const handleMobileMenuAction = (action: string) => {
    setIsMobileMenuOpen(false);
    setActiveView(action as any);
  };

  const handleAuthComplete = (alias: string, profileImg?: string) => {
    if (!activeAuth) return;
    const connId = activeAuth.id;
    setConnections(prev => prev.map(c => c.id === connId ? { ...c, status: 'CONNECTED', accountAlias: alias, profileImg } : c));
    setActiveAuth(null);
  };

  const disconnectBridge = async (id: string) => {
    await fetch(`${DAEMON_URL}/api/v1/channels/${id}/toggle`, {
      method: 'PUT',
      headers: { 'Authorization': `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: false })
    });
    setConnections(prev => prev.map(c =>
      c.id === id ? { ...c, status: 'DISCONNECTED', accountAlias: undefined, profileImg: undefined } : c
    ));
  };

  const startAuthFlow = (conn: Connection) => {
    if (conn.status === 'CONNECTED') {
      disconnectBridge(conn.id);
      return;
    }
    setActiveAuth(conn);
  };

  const copyText = (text: string) => navigator.clipboard.writeText(text);

  const accentColor = isConnected ? '#91D65F' : '#A1A1A1';

  // Render the content area based on activeView
  const renderContent = () => {
    // Ensure we always have connections to show
    const currentConnections = connections && connections.length > 0 ? connections : INITIAL_CONNECTIONS;

    switch (activeView) {
      case 'soul':
        return (
          <div className="inline-panel-wrapper">
            <SoulPreferencesPanel
              onClose={() => setActiveView('chat')}
              onManifestUpdate={(m) => { setBaseManifest(m); geminiServiceRef.current?.setPersonality(m); }}
            />
          </div>
        );
      case 'skills':
        return (
          <div className="inline-panel-wrapper">
            {showSkillWizard ? (
              <SkillBuilderWizard onClose={() => { setShowSkillWizard(false); fetchSkills(); }} />
            ) : (
              <SkillGrid
                skills={skills}
                onSelect={setSelectedSkill}
                onToggle={(id) => setSkills(s => s.map(x => x.id === id ? { ...x, verified: !x.verified } : x))}
                onDelete={() => { }}
                onCreate={() => setShowSkillWizard(true)}
              />
            )}
          </div>
        );
      case 'bridges':
        return (
          <div className="inline-panel-wrapper">
            <BridgeCenter
              connections={currentConnections}
              startAuthFlow={startAuthFlow}
              onSocialAction={handleSocialAction}
              onEnterpriseAction={handleEnterpriseAction}
              onPulse={handlePulse}
            />
          </div>
        );
      case 'api':
        return (
          <div className="inline-panel-wrapper">
            <ApiWizard
              isOpen={true}
              onClose={() => setActiveView('chat')}
              apiKeys={apiKeys}
              onSave={saveApiKeysToDaemon}
            />
          </div>
        );
      case 'wallet':
        return (
          <div className="inline-panel-wrapper">
            <WalletPanel />
          </div>
        );
      case 'memory':
        return (
          <div className="inline-panel-wrapper">
            <MemoryPanel onClose={() => setActiveView('chat')} />
          </div>
        );
      case 'tasks':
        return (
          <div className="inline-panel-wrapper">
            <TaskPanel onClose={() => setActiveView('chat')} />
          </div>
        );
      case 'files':
        return (
          <div className="inline-panel-wrapper">
            <div className="inline-panel">
              <div className="inline-panel__header">
                <h2 className="inline-panel__title">File Manifold</h2>
              </div>
              <div className="inline-panel__body">
                <div className="inline-panel__empty">
                  <p>No files indexed yet.</p>
                  <p className="text-xs opacity-50">Connect an iCloud bridge to sync files.</p>
                </div>
              </div>
            </div>
          </div>
        );
      case 'audit':
        return (
          <div className="inline-panel-wrapper">
            <AuditChainPanel refreshAuditLog={refreshAuditLog} />
          </div>
        );
      case 'canvas':
        return (
          <div className="flex-1 p-4 md:p-8">
            <LiveCanvas nodes={canvasNodes} />
          </div>
        );
      case 'sessions':
        return <SessionsPanel />;
      case 'analytics':
        return <AnalyticsPanel />;
      case 'config':
        return <ConfigPanel />;
      case 'node':
        return <NodePanel />;
      case 'logs':
        return <LogPanel />;
      case 'crons':
        return (
          <div className="inline-panel-wrapper">
            <CronPanel />
          </div>
        );
      case 'agents':
        return <AgentsPanel />;
      case 'debug':
        return <DebugPanel />;
      case 'dag':
        return <DAGPanel />;
      case 'pvt':
        return <PVTDashboard />;
      case 'chat':
      default:
        return (
          <>
            <ModelFallbackBanner />
            <TerminalView
              getFormattedTime={(iso) => new Date(iso).toLocaleTimeString()}
              copyText={copyText}
            />
            <ErrorBoundary>
              <div style={{ position: 'relative' }}>
                <AbortButton
                  abortControllerRef={abortControllerRef}
                  onAbort={() => {
                    setIsProcessing(false);
                    setTranscriptions(prev => [...prev, {
                      text: '[ ABORTED ]: Generation stopped by user.',
                      isUser: false,
                      timestamp: new Date().toISOString()
                    }]);
                  }}
                />
                <CommandBar
                  textInput={textInput}
                  setTextInput={setTextInput}
                  attachments={attachments}
                  handlePaste={handlePaste}
                  removeAttachment={removeAttachment}
                  fileInputRef={fileInputRef}
                  handleFileChange={handleFileChange}
                  handleCommandSubmit={handleCommandSubmit}
                  isProcessing={isProcessing}
                />
              </div>
            </ErrorBoundary>
          </>
        );
    }
  };

  return (
    <div className="app-shell">
      {/* ── Sticky Update Banner ─────────────────────────────────────────── */}
      {updateAvailable && (
        <div className="absolute top-0 left-0 right-0 z-[3000] bg-indigo-600/90 backdrop-blur-xl border-b border-white/10 p-2 flex items-center justify-center gap-4 text-xs font-semibold animate-slide-down">
          <span className="flex items-center gap-2">
            🚀 New version available: <b className="text-white">v{latestVersion}</b>
          </span>
          <button
            onClick={handleSystemUpdate}
            className="bg-white text-indigo-600 px-3 py-1 rounded-full hover:bg-indigo-50 transition-colors shadow-lg"
          >
            Update & Reboot
          </button>
        </div>
      )}

      {/* Onboarding Wizard */}
      {needsOnboarding && <OnboardingWizard />}

      {/* Sprint 3: Exec Approval Modal */}
      <ExecApprovalModal />

      {/* Auth Portal overlay */}
      {activeAuth && <AuthPortal connection={activeAuth} onComplete={handleAuthComplete} onCancel={() => setActiveAuth(null)} />}

      {/* Mobile menu overlay */}
      <MobileMenu isOpen={isMobileMenuOpen} onClose={() => setIsMobileMenuOpen(false)} onAction={handleMobileMenuAction} />

      {/* Top bar */}
      <SystemHeader
        isConnected={isConnected}
        accentColor={accentColor}
        handleConnect={handleConnect}
        sovereignMode={sovereignMode}
        setSovereignMode={setSovereignMode}
      />

      {/* Body: sidebar + main content */}
      <div className="app-shell__body">
        {/* Sidebar */}
        <ErrorBoundary>
          <Sidebar
            audioStream={audioStream as any}
            videoRef={videoRef}
            isCameraActive={isCameraActive}
            toggleCamera={toggleCamera}
            bridgeManagerRef={bridgeManagerRef}
            accentColor={accentColor}
          />
        </ErrorBoundary>

        {/* Main content area */}
        <main
          className={`app-shell__main ${isSidebarCollapsed ? 'app-shell__main--expanded' : ''}`}
          style={{ flexDirection: 'row', display: 'flex' }}
        >
          {/* Central Manifold */}
          <div className="flex-1 flex flex-col h-full relative overflow-hidden">
            {activeNudges.length > 0 && (
              <div className="app-shell__nudges">
                {activeNudges.map(nudge => (
                  <div key={nudge.id} className="app-shell__nudge">
                    <p>{nudge.message}</p>
                    <button onClick={() => setActiveNudges(prev => prev.filter(nx => nx.id !== nudge.id))} className="glass-btn text-xs">Resolve</button>
                  </div>
                ))}
              </div>
            )}
            <ErrorBoundary>
              {renderContent()}
            </ErrorBoundary>
          </div>

          {/* Resizable Artifact Pane */}
          {activeView === 'chat' && (
            <>
              <div className={`pane-resizer ${isResizing ? 'active' : ''}`} onMouseDown={startResizing} />
              <aside className="artifact-pane" style={{ width: artifactWidth }}>
                <div className="artifact-pane__header">
                  <h3 className="artifact-pane__title">Alluci Artifacts</h3>
                  <div className="artifact-pane__subtitle">COGNITIVE_OUTPUT_BUFFER</div>
                </div>
                <div className="artifact-pane__body">
                  <div className="p-10 opacity-20 text-center select-none pointer-events-none mt-20">
                    <div className="mb-4">
                      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" className="mx-auto">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                        <line x1="9" y1="3" x2="9" y2="21" />
                      </svg>
                    </div>
                    <p className="text-[10px] glass-label tracking-widest">Awaiting Artifact</p>
                  </div>
                </div>
              </aside>
            </>
          )}
        </main>
      </div>

      {/* Overlays & Modals */}
      {selectedSkill && (
        <SkillDetailOverlay skill={selectedSkill} onClose={() => setSelectedSkill(null)} />
      )}

      <RpcConsole />
      <ExecApprovalModal />

      {/* Hidden elements */}
      <canvas ref={canvasRef} width={320} height={240} className="hidden" />
    </div>
  );
};

export default App;
