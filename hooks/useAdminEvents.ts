
import { useEffect } from 'react';
import { useStore } from '../store/useStore';
import { adminService } from '../adminService';
import { artifactEvents } from '../lib/artifactEvents';

export const useAdminEvents = () => {
  const {
    accessToken,
    setIsConnected,
    setPendingApproval,
    setActiveNudges,
    setModelFallbackMessage,
    setTranscriptions,
    setPresence,
    setPvtHealth,
    setFlowMode
  } = useStore();

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
            setPresence({
              instances: params.instances || 0,
              sessions: params.sessions || 0
            });
          } else if (method === 'usage.alert') {
            setActiveNudges(prev => [...prev, { id: `usage_${Date.now()}`, message: `Usage Alert: ${params.reason}` }]);
          } else if (method === 'bridge.silenced') {
            setActiveNudges(prev => [...prev, { 
              id: `silenced_${Date.now()}`, 
              message: `🔕 Inbound ${params.protocol} message from ${params.sender} silenced (${params.mode})` 
            }]);
          } else if (method === 'model.fallback') {
            setModelFallbackMessage(`⚠ Primary model unavailable. Using ${params.fallback_model}`);
          } else if (method === 'compaction.status') {
            setTranscriptions(prev => [...prev, {
              text: '',
              isUser: false,
              isCompaction: true,
              tokenCount: params.tokenCount,
              timestamp: new Date().toISOString()
            }]);
          } else if (method === 'manifold.pvt') {
            setPvtHealth({
              P: params.P ?? 0,
              V: params.V ?? 1,
              T: params.T ?? 0,
              psi: params.psi ?? 0,
              coherence: params.coherence ?? 1,
              status: params.status ?? 'HEALTHY',
              isRuptured: params.is_ruptured ?? false,
              phi_total: params.phi_total ?? 0
            });
            if (params.flow_mode) {
              setFlowMode(params.flow_mode);
            }
          } else if (method === 'manifold.rupture') {
            setPvtHealth({ isRuptured: true });
          } else if (method === 'chat.message.received') {
            setTranscriptions(prev => [...prev, {
              id: params.id || `msg_${Date.now()}`,
              text: params.content || params.summary || '',
              isUser: false,
              sender: params.sender || 'rocco',
              timestamp: new Date().toISOString()
            }]);
          } else if (method === 'artifact.created' || method === 'artifact.open' || method === 'orchestrator.artifact.updated') {
            const artifactId = params.artifactId || params.id;
            if (artifactId) {
              artifactEvents.emit({ type: 'artifact.open', artifactId });
            } else if (params.content) {
              const storeState = useStore.getState();
              const setActiveArtifact = storeState.setActiveArtifact;
              const setIsArtifactPaneCollapsed = storeState.setIsArtifactPaneCollapsed;
              const newArtifact = {
                id: `art_${Date.now()}`,
                title: params.title || 'Deep Research Synthesis Report',
                kind: 'text' as const,
                currentVersion: 1,
                content: params.content,
                mimeType: 'text/markdown',
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
              };
              if (setActiveArtifact) {
                setActiveArtifact(newArtifact);
              }
              if (setIsArtifactPaneCollapsed) {
                setIsArtifactPaneCollapsed(false);
              }
            }
          } else if (method === 'security.resolution_required') {
            const { setPendingSecurityResolution } = useStore.getState();
            setPendingSecurityResolution(params);
          }
        },
        onOpen: () => setIsConnected(true),
        onClose: () => setIsConnected(false)
      });
    }
    return () => adminService.disconnect();
  }, [
    accessToken, 
    setPendingApproval, 
    setIsConnected, 
    setActiveNudges, 
    setPresence, 
    setModelFallbackMessage, 
    setTranscriptions, 
    setPvtHealth, 
    setFlowMode
  ]);
};
