import React, { useState, useEffect, useRef, useCallback } from 'react';
import { AlluciGeminiService } from './geminiService';
import { AlluciSovereignService } from './sovereignService';
import { SkillVerifier, AuditLedger, SovereignSecurityManager } from './alluciCore';
import { BridgeManager } from './bridgeManager';
import { useStore } from './store/useStore';
import {
  Connection,
  SkillManifest,
  ApiManifoldKeys
} from './types';
import { INITIAL_CONNECTIONS } from './components/constants';
import { getCsrfToken } from './csrfStore';

// Layout Components
import SystemHeader from './features/system/SystemHeader';
import Sidebar from './components/Sidebar';
import { ErrorBoundary } from './components/ErrorBoundary';

// Content Views
import { MobileMenu } from './components/Visualizers';

// Inline Panels (rendered in main content area)
import { AuthPortal } from './components/AuthPortal';
import { SkillDetailOverlay } from './components/SkillGrid';
import { ToolDetailOverlay } from './components/ToolsPanel';
import SkillBuilderWizard from './components/SkillBuilderWizard';
import ToolBuilderWizard from './components/ToolBuilderWizard';

// Hooks
import { useDaemonStatus } from './hooks/useDaemonStatus';
import { useBiometrics } from './hooks/useBiometrics';
import { useIdentityAuth } from './hooks/useIdentity';
import { useSoulAdaptation } from './hooks/useSoulAdaptation';
import { useSovereignConnection } from './hooks/useConnection';
import { useBridges } from './hooks/useBridges';
import { useInteractions } from './hooks/useInteractions';
import { useAdminEvents } from './hooks/useAdminEvents';
import { useAudioOutput } from './hooks/useAudioOutput';
import { useResizablePane } from './hooks/useResizablePane';
import { useCamera } from './hooks/useCamera';

// Admin & Sprint 3
import { adminService } from './adminService';
import { ExecApprovalModal } from './components/ExecApprovalModal';
import { SecurityInterventionModal } from './components/SecurityInterventionModal';
import { OnboardingWizard } from './features/onboarding/OnboardingWizard';
import { RpcConsole } from './features/system/RpcConsole';

import ViewManifold from './components/ViewManifold';
import './styles/dag.css';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

const App: React.FC = () => {
  const {
    isConnected, setIsConnected,
    isMobileMenuOpen, setIsMobileMenuOpen,
    activeView, setActiveView,
    isSidebarCollapsed,
    setApiKeys,
    connections, setConnections,
    skills, setSkills,
    selectedSkill, setSelectedSkill,
    showSkillWizard, setShowSkillWizard,
    skillToEdit, setSkillToEdit,
    tools, setTools,
    showToolWizard, setShowToolWizard,
    selectedTool, setSelectedTool,
    toolToEdit, setToolToEdit,
    setAuditLog,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    updateAgent,
    setBaseManifest,
    accessToken,
    updateAvailable,
    latestVersion,
    needsOnboarding,
    hydrate,
    activeNudges,
    setActiveNudges,
    operatingMode,
    setOperatingMode
  } = useStore();

  // Core Refs
  const geminiServiceRef = useRef<AlluciGeminiService | null>(null);
  const sovereignServiceRef = useRef<AlluciSovereignService | null>(null);
  const auditLedgerRef = useRef(new AuditLedger(DAEMON_URL));
  const securityManagerRef = useRef(new SovereignSecurityManager(auditLedgerRef.current));
  const bridgeManagerRef = useRef(new BridgeManager(securityManagerRef.current));
  const skillVerifier = useRef(new SkillVerifier());
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Initialization
  useEffect(() => { hydrate(); }, [hydrate]);

  useEffect(() => {
    if (bridgeManagerRef.current) {
      bridgeManagerRef.current.setAccessToken(accessToken);
    }
  }, [accessToken]);

  // Custom Hooks
  useAdminEvents();
  const { handleAudioOutput, audioContextRef, sourcesRef, nextStartTimeRef } = useAudioOutput();
  const { width: artifactWidth, isResizing, startResizing } = useResizablePane('alluci_artifact_width');
  const { videoRef, canvasRef, isCameraActive, toggleCamera } = useCamera(geminiServiceRef, isConnected);

  // Remaining Local States
  const [activeAuth, setActiveAuth] = useState<Connection | null>(null);
  const [sovereignMode, setSovereignMode] = useState(true);
  const [audioStream, setAudioStream] = useState<MediaStream | null>(null);

  // Core Feature Hooks
  useDaemonStatus();
  useBiometrics();
  useIdentityAuth();
  useSoulAdaptation(geminiServiceRef.current);

  const refreshAuditLog = useCallback(() => {
    if (geminiServiceRef.current) setAuditLog(geminiServiceRef.current.audit.getEntries());
  }, [setAuditLog]);

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
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    handleRotateKeys,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    handleFlushCache,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    handleSaveApiKeys,
    handleSocialAction,
    handleEnterpriseAction,
    handlePulse
  } = useBridges(bridgeManagerRef, securityManagerRef, auditLedgerRef, refreshAuditLog);

  const {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    textInput, setTextInput,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    attachments, setAttachments,
    handleCommandSubmit,
    handleFileChange,
    handlePaste,
    removeAttachment,
    abortControllerRef
  } = useInteractions(geminiServiceRef, isConnected, handleAudioOutput, refreshAuditLog, fileInputRef, sovereignMode);

  const saveApiKeysToDaemon = async (keys: ApiManifoldKeys) => {
    try {
      const token = accessToken || localStorage.getItem('alluci_access_token');
      if (!token) {
        console.error("No access token available for key save");
        return;
      }

      const csrfToken = await getCsrfToken(DAEMON_URL, token);
      const res = await fetch(`${DAEMON_URL}/api/v1/vault/keys`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
        },
        body: JSON.stringify(keys),
        credentials: 'include'
      });
      if (res.ok) setApiKeys(keys);
      else {
          const err = await res.json().catch(() => ({ detail: res.statusText }));
          console.error("Save failed:", err.detail);
      }
    } catch (e) { console.error("Failed to save keys", e); }
  };

  useEffect(() => {
    geminiServiceRef.current = new AlluciGeminiService();
    const loadInitialData = async () => {
      try {
        const token = localStorage.getItem('alluci_access_token');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

        const res = await fetch(`${DAEMON_URL}/api/v1/vault/keys`, { 
          headers,
          credentials: 'include' 
        });
        if (res.ok) {
          const keys = await res.json();
          if (keys && Object.keys(keys).length > 0) setApiKeys(keys);
        }
        const soulRes = await fetch(`${DAEMON_URL}/api/v1/soul/manifest`, { 
          headers,
          credentials: 'include' 
        });
        if (soulRes.ok) {
          const manifest = await soulRes.json();
          if (manifest) {
            geminiServiceRef.current?.setPersonality(manifest);
            setBaseManifest(manifest);
          }
        }
      } catch (e) {
        console.error("[App] loadInitialData failed:", e);
        setIsConnected(false);
        // We log the connection failure locally
        if (geminiServiceRef.current) {
          await geminiServiceRef.current.audit.addEntry('SYSTEM_CONNECTION_FAILURE', { error: "Daemon offline or unreachable" });
          setAuditLog(geminiServiceRef.current.audit.getEntries());
        }
      }
    };
    loadInitialData();
    if (connections.length === 0) setConnections(INITIAL_CONNECTIONS);
    return () => geminiServiceRef.current?.disconnect();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchSkills = useCallback(async () => {
    const core = skillVerifier.current.getManifests();
    try {
      const token = accessToken || localStorage.getItem('alluci_access_token');
      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch(`${DAEMON_URL}/api/v1/registry/skills`, { 
        headers,
        credentials: 'include' 
      });
      if (res.ok) {
        const data = await res.json();
        const custom = data.skills || [];
        // Create a map to prioritize vault over core
        const skillMap = new Map();
        core.forEach((c: SkillManifest) => skillMap.set(c.id, c));
        custom.forEach((c: SkillManifest) => skillMap.set(c.id, c));
        
        setSkills(Array.from(skillMap.values()));
        return;
      }
    // eslint-disable-next-line no-empty
    } catch (e) { }
    setSkills(core);
  }, [setSkills, accessToken]);

  const fetchTools = useCallback(async () => {
    try {
      const token = accessToken || localStorage.getItem('alluci_access_token');
      const headers: Record<string, string> = {};
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const res = await fetch(`${DAEMON_URL}/api/v1/registry/tools`, { 
        headers,
        credentials: 'include' 
      });
      if (res.ok) {
        const data = await res.json();
        setTools(data.tools || []);
      }
    // eslint-disable-next-line no-empty
    } catch (e) { }
  }, [setTools, accessToken]);

  useEffect(() => { 
    fetchSkills(); 
    fetchTools();
  }, [fetchSkills, fetchTools]);

  const handleAuthComplete = (alias: string, profileImg?: string) => {
    if (!activeAuth) return;
    const connId = activeAuth.id;
    setConnections(prev => prev.map(c => c.id === connId ? { ...c, status: 'CONNECTED', accountAlias: alias, profileImg } : c));
    setActiveAuth(null);
  };

  const disconnectBridge = async (id: string) => {
    const csrfToken = await getCsrfToken(DAEMON_URL, accessToken);
    await fetch(`${DAEMON_URL}/api/v1/channels/${id}/toggle`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
        ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
      },
      body: JSON.stringify({ enabled: false }),
      credentials: 'include',
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

  const handleSystemUpdate = useCallback(() => {
    if (window.confirm(`Initiate daemon update to v${latestVersion}? System will reboot.`)) {
      adminService.sendRPC('system.update', {});
    }
  }, [latestVersion]);

  const accentColor = isConnected ? '#91D65F' : '#A1A1A1';

  return (
    <div className="app-shell">
      {updateAvailable && (
        <div className="absolute top-0 left-0 right-0 z-[3000] bg-indigo-600/90 backdrop-blur-xl border-b border-white/10 p-2 flex items-center justify-center gap-4 text-xs font-semibold animate-slide-down">
          <span className="flex items-center gap-2">
            🚀 New version available: <b className="text-white">v{latestVersion}</b>
          </span>
          <button onClick={handleSystemUpdate} className="bg-white text-indigo-600 px-3 py-1 rounded-full hover:bg-indigo-50 transition-colors shadow-lg">
            Update & Reboot
          </button>
        </div>
      )}

      {needsOnboarding && <OnboardingWizard />}
      <ExecApprovalModal />
      <SecurityInterventionModal />
      {activeAuth && <AuthPortal connection={activeAuth} onComplete={handleAuthComplete} onCancel={() => setActiveAuth(null)} />}
      <MobileMenu isOpen={isMobileMenuOpen} onClose={() => setIsMobileMenuOpen(false)} onAction={(v) => { setIsMobileMenuOpen(false); setActiveView(v as import('./store/useStore').ActiveView); }} />

      <SystemHeader isConnected={isConnected} accentColor={accentColor} handleConnect={handleConnect} sovereignMode={sovereignMode} setSovereignMode={setSovereignMode} />

      <div className="app-shell__body">
        <ErrorBoundary>
          <Sidebar audioStream={audioStream} videoRef={videoRef} isCameraActive={isCameraActive} toggleCamera={toggleCamera} bridgeManagerRef={bridgeManagerRef} accentColor={accentColor} />
        </ErrorBoundary>

        <main className={`app-shell__main ${isSidebarCollapsed ? 'app-shell__main--expanded' : ''}`} style={{ flexDirection: 'row', display: 'flex' }}>
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
              <ViewManifold
                geminiServiceRef={geminiServiceRef}
                bridgeManagerRef={bridgeManagerRef}
                fetchSkills={fetchSkills}
                startAuthFlow={startAuthFlow}
                handleSocialAction={handleSocialAction}
                handleEnterpriseAction={handleEnterpriseAction}
                handlePulse={handlePulse}
                saveApiKeysToDaemon={saveApiKeysToDaemon}
                refreshAuditLog={refreshAuditLog}
                abortControllerRef={abortControllerRef}
                fileInputRef={fileInputRef}
                handleFileChange={handleFileChange}
                handleCommandSubmit={handleCommandSubmit}
                handlePaste={handlePaste}
                removeAttachment={removeAttachment}
              />
            </ErrorBoundary>
          </div>

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
                    <p className="text-[10px] glass-label tracking-widest">Awaiting Artifact</p>
                  </div>
                </div>
              </aside>
            </>
          )}
        </main>
      </div>

      {selectedSkill && <SkillDetailOverlay skill={selectedSkill} onClose={() => setSelectedSkill(null)} onEdit={(skill) => { setSelectedSkill(null); setSkillToEdit(skill); setShowSkillWizard(true); setActiveView('skills'); }} />}
      {showSkillWizard && <SkillBuilderWizard onClose={() => setShowSkillWizard(false)} />}
      {showToolWizard && <ToolBuilderWizard onClose={() => setShowToolWizard(false)} />}
      {selectedTool && <ToolDetailOverlay tool={selectedTool} onClose={() => setSelectedTool(null)} onEdit={(tool) => { setSelectedTool(null); setToolToEdit(tool); setShowToolWizard(true); setActiveView('tools'); }} />}
      <RpcConsole />
      <canvas ref={canvasRef} width={320} height={240} className="hidden" />
    </div>
  );
};

export default App;

