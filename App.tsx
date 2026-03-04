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
    isProcessing, setIsProcessing
  } = useStore();

  // Core Refs
  const geminiServiceRef = useRef<AlluciGeminiService | null>(null);
  const sovereignServiceRef = useRef<AlluciSovereignService | null>(null);
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
    removeAttachment
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
      const res = await fetch(`${DAEMON_URL}/api/vault/keys`, {
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
        const res = await fetch(`${DAEMON_URL}/api/vault/keys`, { credentials: 'include' });
        if (res.ok) {
          const keys = await res.json();
          if (keys && Object.keys(keys).length > 0) setApiKeys(keys);
        }
        const soulRes = await fetch(`${DAEMON_URL}/soul/manifest`, { credentials: 'include' });
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
      const res = await fetch(`${DAEMON_URL}/skills`, { credentials: 'include' });
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

  const startAuthFlow = async (conn: Connection) => {
    if (conn.status === 'CONNECTED') {
      setConnections(prev => prev.map(c => c.id === conn.id ? { ...c, status: 'DISCONNECTED', accountAlias: undefined, profileImg: undefined } : c));
      return;
    }
    const initialized = await bridgeManagerRef.current.initializeBridge(conn);
    if (!initialized) return;
    setActiveAuth(conn);
  };

  const copyText = (text: string) => navigator.clipboard.writeText(text);

  const accentColor = isConnected ? '#91D65F' : '#A1A1A1';

  const groupedConnections = {
    'APPLE_ECOSYSTEM': connections.filter(c => ['icloud', 'imessage', 'iwatch', 'iphone'].includes(c.id)),
    'SOCIAL_MANIFOLD': connections.filter(c => ['wa', 'tg', 'dc', 'sg', 'ig', 'fb', 'x'].includes(c.id)),
    'ENTERPRISE_CORE': connections.filter(c => ['sl', 'mt', 'gm', 'gd', 'webchat', 'wechat'].includes(c.id)),
    'VERUS_IDENTITY': connections.filter(c => ['verus'].includes(c.id))
  };

  // Render the content area based on activeView
  const renderContent = () => {
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
              groupedConnections={groupedConnections}
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
      case 'chat':
      default:
        return (
          <>
            <TerminalView
              getFormattedTime={(iso) => new Date(iso).toLocaleTimeString()}
              copyText={copyText}
            />
            <ErrorBoundary>
              <CommandBar
                textInput={textInput}
                setTextInput={setTextInput}
                attachments={attachments}
                removeAttachment={removeAttachment}
                fileInputRef={fileInputRef}
                handleFileChange={handleFileChange}
                handleCommandSubmit={handleCommandSubmit}
                isProcessing={isProcessing}
              />
            </ErrorBoundary>
          </>
        );
    }
  };

  return (
    <div className="app-shell">
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
        <main className={`app-shell__main ${isSidebarCollapsed ? 'app-shell__main--expanded' : ''}`}>
          {/* Nudges */}
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
        </main>
      </div>

      {/* Skill detail overlay */}
      {selectedSkill && (
        <SkillDetailOverlay skill={selectedSkill} onClose={() => setSelectedSkill(null)} />
      )}

      {/* Hidden elements */}
      <canvas ref={canvasRef} width={320} height={240} className="hidden" />
    </div>
  );
};

export default App;
