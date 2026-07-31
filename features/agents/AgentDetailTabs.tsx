import React, { useState, useEffect } from 'react';
import { useStore } from '../../store/useStore';
import { getCsrfToken } from '../../csrfStore';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { ChevronLeft, AlertTriangle, Save, Layout, Box, Wrench, Network, Clock, Zap, Activity, History, RefreshCw, Cpu } from 'lucide-react';
import { HeartbeatOrderEditor } from '../heartbeat/HeartbeatOrderEditor';
import WorkspaceEditor from './WorkspaceEditor';
import ToolProfileEditor from './ToolProfileEditor';
import SkillProfileEditor from './SkillProfileEditor';
import ChannelSubscriptions from './ChannelSubscriptions';
import BulkSkillActions from '../skills/BulkSkillActions';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import NodeBindingEditor from '../devices/NodeBindingEditor';
import EngineMatrixEditor from './EngineMatrixEditor';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

interface AgentDetailProps {
    agentId: string;
    onBack: () => void;
}

export const AgentDetailTabs: React.FC<AgentDetailProps> = ({ agentId, onBack }) => {
    const { accessToken, availableModels, loadAvailableModels } = useStore();
    const [activeTab, setActiveTab] = useState<'overview' | 'workspace' | 'tools' | 'channels' | 'heartbeat' | 'skills' | 'engine'>('overview');
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [agent, setAgent] = useState<any>(null);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [heartbeatHistory, setHeartbeatHistory] = useState<any[]>([]);
    const [availableProfiles, setAvailableProfiles] = useState<{id: string, name: string}[]>([]);
    const [saving, setSaving] = useState(false);
    const [showPiiModal, setShowPiiModal] = useState(false);
    const [pendingPiiState, setPendingPiiState] = useState(false);

    useEffect(() => {
        if (accessToken) {
            loadAvailableModels(accessToken);
        }
    }, [accessToken, loadAvailableModels]);

    const fetchHeartbeatHistory = async () => {
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/agents/${agentId}/heartbeat/history`, {
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            });
            if (res.ok) {
                const data = await res.json();
                setHeartbeatHistory(data.history || []);
            }
        } catch (err) {
            console.error('Failed fetching heartbeat history:', err);
        }
    };

    useEffect(() => {
        const load = async () => {
            try {
                const res = await fetch(`${DAEMON_URL}/api/v1/agents/${agentId}`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include'
                });
                if (res.ok) {
                    const data = await res.json();
                    setAgent(data.agent);
                }
            } catch (err) {
                console.error('Failed fetching agent mapping:', err);
            }
        };

        const loadProfiles = async () => {
            try {
                const res = await fetch(`${DAEMON_URL}/api/v1/soul/profiles`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include'
                });
                if (res.ok) {
                    const data = await res.json();
                    setAvailableProfiles(data.profiles || []);
                }
            } catch (err) {
                console.error('Failed fetching available profiles:', err);
            }
        };
        load();
        loadProfiles();
        if (activeTab === 'heartbeat') fetchHeartbeatHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [agentId, accessToken, activeTab]);

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const handleSaveAgent = async (updatedData: any) => {
        setSaving(true);
        try {
            const payload = { ...updatedData };
            if (typeof payload.engine_manifest === 'string') {
                try {
                    payload.engine_manifest = JSON.parse(payload.engine_manifest);
                } catch (e) {
                    console.error("Failed to parse engine_manifest string prior to saving:", e);
                }
            }

            const csrfToken = await getCsrfToken(DAEMON_URL, accessToken);
            const res = await fetch(`${DAEMON_URL}/api/v1/agents/${agentId}`, {
                method: 'PUT',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`,
                    ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {})
                },
                body: JSON.stringify(payload),
                credentials: 'include'
            });
            if (res.ok) {
                setAgent({ ...agent, ...payload });
            }
        } catch (err) {
            console.error('Failed saving agent:', err);
        } finally {
            setSaving(false);
        }
    };

    if (!agent) {
        return <div className="p-8 text-center text-xs font-mono opacity-50 tracking-widest">DECRYPTING_AGENT_MANIFEST...</div>;
    }

    return (
        <div className="w-full flex flex-col gap-4 h-full p-4 lg:p-6 mx-auto max-w-7xl">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-glass-edge pb-4">
                <div className="flex items-center gap-4">
                    <button
                        onClick={onBack}
                        className="glass-btn flex items-center justify-center p-2 rounded-xl text-text-tertiary hover:text-accent border-none bg-glass-1 shadow-sm"
                    >
                        <ChevronLeft size={16} />
                    </button>
                    <div>
                        <h2 className="text-xl font-medium tracking-tight text-text-primary flex items-center gap-3">
                            {agent.name}
                            <span className="text-[10px] font-mono opacity-40 glass-tag bg-glass-pressed border-none tracking-widest">{agentId}</span>
                        </h2>
                        <span className="text-[11px] text-text-tertiary">Agent Manifold Engine Control</span>
                    </div>
                </div>

                <div className="flex bg-glass-1 border border-glass-edge p-1 rounded-xl shadow-lg shadow-black/20 overflow-x-auto">
                    {[
                        { id: 'overview', icon: Layout, label: 'Overview' },
                        { id: 'engine', icon: Cpu, label: 'Engine Matrix' },
                        { id: 'workspace', icon: Box, label: 'Workspace' },
                        { id: 'tools', icon: Wrench, label: 'Tools' },
                        { id: 'channels', icon: Network, label: 'Channels' },
                        { id: 'heartbeat', icon: Activity, label: 'Heartbeat' },
                        { id: 'skills', icon: Zap, label: 'Skills' }
                    ].map(tab => (
                        <button
                            key={tab.id}
                            // eslint-disable-next-line @typescript-eslint/no-explicit-any
                            onClick={() => setActiveTab(tab.id as any)}
                            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-[11px] font-medium transition-all whitespace-nowrap ${activeTab === tab.id ? 'bg-glass-pressed text-accent shadow-sm' : 'text-text-tertiary hover:text-text-primary'}`}
                        >
                            <tab.icon size={12} /> {tab.label}
                        </button>
                    ))}
                </div>
            </div>

            <div className="flex-1 overflow-y-auto w-full pt-2">

                {/* ── OVERVIEW TAB ── */}
                {activeTab === 'overview' && (
                    <div className="flex flex-col gap-6 max-w-2xl animate-in fade-in zoom-in-95 duration-300">
                        <div className="bg-glass-1 border border-glass-edge p-5 rounded-xl flex flex-col gap-4">
                            <h3 className="glass-label text-[10px] uppercase opacity-70 border-b border-glass-edge pb-2 mb-2">Core Identity Matrices</h3>

                            <div className="flex flex-col gap-1">
                                <label className="text-[10px] text-text-tertiary">Manifold Designation Name</label>
                                <input
                                    className="glass-input text-sm w-full font-medium"
                                    value={agent.name || ''}
                                    onChange={e => setAgent({ ...agent, name: e.target.value })}
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="flex flex-col gap-1">
                                    <label className="text-[10px] text-text-tertiary">Operational Status</label>
                                    <select
                                        className="glass-input text-xs w-full bg-glass-1 border border-glass-edge text-text-primary py-2 px-3 rounded-lg"
                                        value={agent.status || 'DRAFT'}
                                        onChange={e => setAgent({ ...agent, status: e.target.value })}
                                    >
                                        <option value="DRAFT">Draft (Offline)</option>
                                        <option value="READY">Ready (Standby)</option>
                                        <option value="ACTIVE">Active (Online)</option>
                                        <option value="ERROR">Error (Halted)</option>
                                    </select>
                                </div>
                                <div className="flex flex-col gap-1">
                                    <label className="text-[10px] text-text-tertiary">Designation Description</label>
                                    <input
                                        className="glass-input text-xs w-full h-[34px]"
                                        value={agent.description || ''}
                                        onChange={e => setAgent({ ...agent, description: e.target.value })}
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="flex flex-col gap-1">
                                    <label className="text-[10px] text-text-tertiary">Primary Engine Model</label>
                                    <select
                                        className="glass-input text-xs w-full bg-glass-1 border border-glass-edge text-text-primary py-2 px-3 rounded-lg"
                                        value={agent.model || ''}
                                        onChange={e => setAgent({ ...agent, model: e.target.value })}
                                    >
                                        <option value="">Select Engine...</option>
                                        {Array.from(new Set([...availableModels.map(m => m.category || 'API'), 'Local', 'API', 'Token Router', 'Open'])).filter(Boolean).map(cat => {
                                            const catModels = availableModels.filter(m => (m.category || 'API') === cat);
                                            if (catModels.length === 0) return null;
                                            return (
                                                <optgroup key={cat} label={cat}>
                                                    {catModels.map(m => (
                                                        <option key={m.id} value={m.id}>{m.name}</option>
                                                    ))}
                                                </optgroup>
                                            );
                                        })}
                                    </select>
                                    <div className="mt-3 bg-glass-2 border border-glass-edge rounded-lg p-2 flex items-center justify-between">
                                        <div className="flex flex-col">
                                            <span className="text-[10px] font-medium text-text-primary">Direct Routing (Unfiltered)</span>
                                            <span className="text-[9px] text-text-tertiary">Bypass local PII proxy for Teacher Models</span>
                                        </div>
                                        <button
                                            className={`relative inline-flex h-4 w-8 items-center rounded-full transition-colors ${agent.pii_override_enabled ? 'bg-red-500/80' : 'bg-glass-edge'}`}
                                            onClick={() => {
                                                const newState = !agent.pii_override_enabled;
                                                if (newState) {
                                                    setPendingPiiState(newState);
                                                    setShowPiiModal(true);
                                                } else {
                                                    setAgent({ ...agent, pii_override_enabled: false });
                                                }
                                            }}
                                        >
                                            <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${agent.pii_override_enabled ? 'translate-x-4' : 'translate-x-1'}`} />
                                        </button>
                                    </div>
                                </div>
                                <div className="flex flex-col gap-1">
                                    <label className="text-[10px] text-text-tertiary opacity-70">Fallback Chain Sequence</label>
                                    <div className="flex flex-col gap-2">
                                        <div className="flex flex-wrap gap-1 items-center bg-glass-pressed border border-glass-edge p-1.5 rounded-lg min-h-[36px]">
                                            {agent.fallback ? agent.fallback.split(',').map((fb: string, idx: number) => {
                                                const cleanFb = fb.trim();
                                                if (!cleanFb) return null;
                                                const found = availableModels.find(m => m.id === cleanFb);
                                                return (
                                                    <span key={idx} className="flex items-center gap-1 bg-glass-1 text-accent px-2 py-0.5 rounded text-[10px] font-mono border border-glass-edge shadow-sm">
                                                        {found ? found.name : cleanFb}
                                                        <button 
                                                            className="opacity-50 hover:opacity-100 hover:text-red-400 ml-1 outline-none"
                                                            onClick={() => {
                                                                const newFb = agent.fallback.split(',').map((s: string) => s.trim()).filter((s: string) => s && s !== cleanFb).join(',');
                                                                setAgent({ ...agent, fallback: newFb });
                                                            }}
                                                        >×</button>
                                                    </span>
                                                );
                                            }) : <span className="text-[10px] text-text-tertiary opacity-50 italic px-1">No fallbacks</span>}
                                        </div>
                                        <select
                                            className="glass-input text-[10px] w-full bg-glass-1 border border-glass-edge text-text-tertiary py-1 px-2 rounded-lg"
                                            value=""
                                            onChange={e => {
                                                if (!e.target.value) return;
                                                const current = agent.fallback ? agent.fallback.split(',').map((s: string) => s.trim()).filter(Boolean) : [];
                                                if (!current.includes(e.target.value)) {
                                                    setAgent({ ...agent, fallback: [...current, e.target.value].join(',') });
                                                }
                                            }}
                                        >
                                            <option value="">+ Add Fallback Model</option>
                                            {Array.from(new Set([...availableModels.map(m => m.category || 'API'), 'Local', 'API', 'Token Router', 'Open'])).filter(Boolean).map(cat => {
                                                const catModels = availableModels.filter(m => (m.category || 'API') === cat);
                                                if (catModels.length === 0) return null;
                                                return (
                                                    <optgroup key={cat} label={cat}>
                                                        {catModels.map(m => (
                                                            <option key={m.id} value={m.id}>{m.name}</option>
                                                        ))}
                                                    </optgroup>
                                                );
                                            })}
                                        </select>
                                    </div>
                                </div>
                            </div>

                            <div className="flex flex-col gap-1 h-full mt-2">
                                <label className="text-[10px] text-text-tertiary uppercase flex justify-between">
                                    <span>System Prompt DNA</span>
                                    <span className="text-accent opacity-60">System Overrides Root</span>
                                </label>
                                <textarea
                                    className="glass-input mt-1 w-full text-[11px] font-mono text-text-secondary h-48 resize-none p-3"
                                    value={agent.system_prompt || 'You are a Sovereign Agent. Autonomous. Secure.'}
                                    onChange={e => setAgent({ ...agent, system_prompt: e.target.value })}
                                />
                            </div>

                            <div className="flex flex-col gap-1 mt-2">
                                <label className="text-[10px] text-text-tertiary uppercase flex justify-between">
                                    <span>Soul Profile Architecture</span>
                                    <span className="text-accent opacity-60">Cognitive Framework</span>
                                </label>
                                <select
                                    className="glass-input mt-1 w-full text-sm font-medium bg-glass-1 border border-glass-edge py-2 px-3 rounded-lg text-text-primary"
                                    value={agent.soul_profile_id || ''}
                                    onChange={e => setAgent({ ...agent, soul_profile_id: e.target.value })}
                                >
                                    <option value="">Core Executive (Global Default)</option>
                                    {availableProfiles.map(p => (
                                        <option key={p.id} value={p.id}>{p.name}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="flex justify-end pt-4">
                                <button className="glass-btn flex items-center gap-2 px-6 py-2" onClick={() => handleSaveAgent(agent)} disabled={saving}>
                                    <Save size={14} /> {saving ? 'Writing OS...' : 'Save Overview Manifest'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* ── WORKSPACE TAB ── */}
                {activeTab === 'workspace' && <WorkspaceEditor agentId={agentId} />}

                {/* ── ENGINE MATRIX TAB ── */}
                {activeTab === 'engine' && (
                    <EngineMatrixEditor 
                        agentId={agentId} 
                        engineManifest={agent.engine_manifest} 
                        onSave={(manifest) => handleSaveAgent({ engine_manifest: manifest })}
                    />
                )}

                {/* ── TOOLS TAB ── */}
                {activeTab === 'tools' && <ToolProfileEditor agentId={agentId} />}

                {/* ── CHANNELS TAB ── */}
                {activeTab === 'skills' && <SkillProfileEditor agentId={agentId} />}
                {activeTab === 'channels' && <ChannelSubscriptions agentId={agentId} />}

                {/* ── HEARTBEAT TAB ── */}
                {activeTab === 'heartbeat' && (
                    <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                            <div className="lg:col-span-2 space-y-4">
                                <div className="bg-glass-1 border border-glass-edge p-6 rounded-2xl shadow-xl">
                                    <HeartbeatOrderEditor 
                                        agentId={agentId}
                                        initialOrders={agent.heartbeat_orders || []}
                                        onSave={(orders) => handleSaveAgent({ heartbeat_orders: orders })}
                                    />
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div className="bg-glass-1 border border-glass-edge p-5 rounded-2xl shadow-lg">
                                    <h4 className="text-[10px] uppercase tracking-widest text-text-tertiary font-bold mb-4 flex items-center gap-2">
                                        <History className="w-3 h-3 text-accent" />
                                        Recent Pulse Events
                                    </h4>
                                    
                                    <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
                                        {heartbeatHistory.length === 0 && (
                                            <div className="py-8 text-center text-[10px] font-mono opacity-30 italic">
                                                NO_RECENT_PULSE_DATA
                                            </div>
                                        )}
                                        {heartbeatHistory.map((entry, i) => (
                                            <div key={i} className="p-3 bg-glass-pressed rounded-xl border border-glass-edge flex flex-col gap-2">
                                                <div className="flex justify-between items-start">
                                                  <span className="text-[10px] font-bold text-accent px-1.5 py-0.5 bg-accent/10 rounded uppercase">
                                                    {entry.outcome}
                                                  </span>
                                                  <span className="text-[9px] font-mono opacity-40">
                                                    {new Date(entry.fired_at * 1000).toLocaleTimeString()}
                                                  </span>
                                                </div>
                                                <div className="text-[11px] font-medium text-text-secondary leading-relaxed">
                                                    {entry.probe_type} → {entry.action_type}
                                                </div>
                                                <div className="text-[9px] text-text-quaternary font-mono line-clamp-2">
                                                    {entry.detail}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                    
                                    <button 
                                        onClick={fetchHeartbeatHistory}
                                        className="w-full mt-4 py-2 text-[10px] font-bold text-text-tertiary hover:text-accent flex items-center justify-center gap-2 transition-colors border-t border-glass-edge pt-4"
                                    >
                                        <RefreshCw className="w-3 h-3" />
                                        Refresh Telemetry
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

            </div>


            {/* PII Override Warning Modal */}
            {showPiiModal && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
                    <div className="bg-glass-1 border border-red-500/30 rounded-xl p-6 max-w-md w-full shadow-2xl relative overflow-hidden">
                        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-red-500/50 to-orange-500/50"></div>
                        <div className="flex items-start gap-4 mb-4">
                            <div className="p-3 bg-red-500/10 rounded-lg text-red-400">
                                <AlertTriangle size={24} />
                            </div>
                            <div>
                                <h3 className="text-lg font-medium text-text-primary">Disable Privacy Protection?</h3>
                                <p className="text-xs text-text-secondary mt-1 leading-relaxed">
                                    You are about to disable the AlluciSecureProxy for this sub-agent. This means <strong>all prompts and data</strong> routed to external Teacher Models will bypass local PII scrubbing and anonymization.
                                </p>
                            </div>
                        </div>
                        <div className="bg-glass-pressed border border-glass-edge p-3 rounded-lg text-[10px] text-text-tertiary mb-6">
                            Only disable this if the external model explicitly requires full, unmodified context to perform its task (e.g. complex coding tasks or specific external integrations).
                        </div>
                        <div className="flex justify-end gap-3">
                            <button
                                onClick={() => setShowPiiModal(false)}
                                className="px-4 py-2 rounded-lg text-xs font-medium text-text-secondary hover:text-text-primary hover:bg-glass-2 transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => {
                                    setAgent({ ...agent, pii_override_enabled: pendingPiiState });
                                    setShowPiiModal(false);
                                }}
                                className="px-4 py-2 rounded-lg text-xs font-medium bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/30 transition-colors"
                            >
                                I Understand, Disable Protection
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AgentDetailTabs;
