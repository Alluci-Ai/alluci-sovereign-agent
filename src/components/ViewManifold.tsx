import React, { Suspense } from 'react';
import { useStore } from '../store/useStore';
import { ErrorBoundary } from './ErrorBoundary';

// Features
import TerminalView from '../features/terminal/TerminalView';
import CommandBar from '../features/terminal/CommandBar';
import AuditChainPanel from '../features/system/AuditChainPanel';
import LiveCanvas from './LiveCanvas';
import SoulPreferencesPanel from './SoulPreferencesPanel';
import SkillBuilderWizard from './SkillBuilderWizard';
import ApiWizard from './ApiWizard';
import { TaskPanel } from './TaskPanel';
import BridgeCenter from './BridgeCenter';
import { SkillGrid } from './SkillGrid';
import { AbortButton } from '../features/chat/AbortButton';
import { ModelFallbackBanner } from '../features/chat/ModelFallbackBanner';
import { SessionsPanel } from '../features/sessions/SessionsPanel';
import { AnalyticsPanel } from '../features/analytics/AnalyticsPanel';
import { ConfigPanel } from '../features/config/ConfigPanel';
import { LogPanel } from '../features/observability/LogPanel';
import { AgentsPanel } from '../features/agents/AgentsPanel';
import { DebugPanel } from '../features/debug/DebugPanel';
import CronPanel from '../features/scheduling/CronPanel';
import { WalletPanel } from '../features/wallet/WalletPanel';
import { NodePanel } from '../features/wallet/NodePanel';
import { MemoryPanel } from '../features/memory/MemoryPanel';
import { DAGPanel } from '../features/dag/DAGPanel';
import PVTDashboard from '../features/observability/PVTDashboard';

interface ViewManifoldProps {
  geminiServiceRef: any;
  bridgeManagerRef: any;
  fetchSkills: () => void;
  startAuthFlow: (conn: any) => void;
  handleSocialAction: (action: string) => void;
  handleEnterpriseAction: (action: string) => void;
  handlePulse: () => void;
  saveApiKeysToDaemon: (keys: any) => void;
  refreshAuditLog: () => void;
  abortControllerRef: any;
  fileInputRef: any;
  handleFileChange: (e: any) => void;
  handleCommandSubmit: (e: any) => void;
  handlePaste: (e: any) => void;
  removeAttachment: (id: string) => void;
}

const ViewManifold: React.FC<ViewManifoldProps> = ({
  geminiServiceRef,
  fetchSkills,
  startAuthFlow,
  handleSocialAction,
  handleEnterpriseAction,
  handlePulse,
  saveApiKeysToDaemon,
  refreshAuditLog,
  abortControllerRef,
  fileInputRef,
  handleFileChange,
  handleCommandSubmit,
  handlePaste,
  removeAttachment
}) => {
  const {
    activeView, setActiveView,
    connections,
    showSkillWizard, setShowSkillWizard,
    skills, setSkills,
    setSelectedSkill,
    apiKeys,
    canvasNodes,
    setIsProcessing,
    setTranscriptions,
    textInput, setTextInput,
    attachments,
    isProcessing,
    setBaseManifest
  } = useStore();

  const copyText = (text: string) => navigator.clipboard.writeText(text);

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
              onToggle={(id) => setSkills(skills.map(x => x.id === id ? { ...x, verified: !x.verified } : x))}
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
            connections={connections}
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
      return <div className="inline-panel-wrapper"><WalletPanel /></div>;
    case 'memory':
      return <div className="inline-panel-wrapper"><MemoryPanel onClose={() => setActiveView('chat')} /></div>;
    case 'tasks':
      return <div className="inline-panel-wrapper"><TaskPanel onClose={() => setActiveView('chat')} /></div>;
    case 'files':
      return (
        <div className="inline-panel-wrapper">
          <div className="inline-panel">
            <div className="inline-panel__header"><h2 className="inline-panel__title">File Manifold</h2></div>
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
      return <div className="inline-panel-wrapper"><AuditChainPanel refreshAuditLog={refreshAuditLog} /></div>;
    case 'canvas':
      return <div className="flex-1 p-4 md:p-8"><LiveCanvas nodes={canvasNodes} /></div>;
    case 'sessions': return <SessionsPanel />;
    case 'analytics': return <AnalyticsPanel />;
    case 'config': return <ConfigPanel />;
    case 'node': return <NodePanel />;
    case 'logs': return <LogPanel />;
    case 'crons': return <div className="inline-panel-wrapper"><CronPanel /></div>;
    case 'agents': return <AgentsPanel />;
    case 'debug': return <DebugPanel />;
    case 'dag': return <DAGPanel />;
    case 'pvt': return <PVTDashboard />;
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

export default ViewManifold;
