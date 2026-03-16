import React, { useState, useEffect } from 'react';
import { useStore } from '../../store/useStore';
import { Bot, UserPlus, Settings, Activity, Network } from 'lucide-react';
import AgentDetailTabs from './AgentDetailTabs';
import AgentDirtyIndicator from './AgentDirtyIndicator';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

export const AgentsPanel: React.FC = () => {
    const { accessToken } = useStore();
    const [agents, setAgents] = useState<any[]>([]);
    const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchAgents = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/agents`, {
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            });
            if (res.ok) {
                const data = await res.json();
                setAgents(data.agents || []);
            }
        } catch (err) {
            console.error('[AgentsPanel] Initial sync failed', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAgents();
    }, [accessToken]);

    const handleCreate = async () => {
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/agents`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name: 'New Agent Model', model: 'gpt-4o', status: 'DRAFT', active_skills: 0, channels: 0 }),
                credentials: 'include'
            });
            if (res.ok) {
                const data = await res.json();
                setAgents([...agents, data.agent]);
                setSelectedAgentId(data.agent.id);
            }
        } catch (e) {
            console.error('Failed to create stub agent:', e);
        }
    };

    if (selectedAgentId) {
        return (
            <AgentDetailTabs
                agentId={selectedAgentId}
                onBack={() => { setSelectedAgentId(null); fetchAgents(); }}
            />
        );
    }

    return (
        <div className="inline-panel-wrapper overflow-auto">
            <div className="max-w-7xl mx-auto w-full flex flex-col gap-6 lg:p-6 p-4 h-full">

                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-glass-edge pb-4">
                    <div className="flex items-center gap-3">
                        <Bot size={20} className="text-accent" />
                        <h2 className="text-xl font-medium tracking-tight text-text-primary">Agent Constellation</h2>
                    </div>

                    <button
                        onClick={handleCreate}
                        className="glass-btn flex items-center gap-2"
                    >
                        <UserPlus size={14} /> Initialize Sovereign Agent
                    </button>
                </div>

                <div className="bg-glass-1 border border-glass-edge rounded-xl overflow-hidden min-h-[500px] flex flex-col relative">
                    <Activity className="absolute -right-10 -bottom-10 opacity-[0.02] text-accent" size={200} pointerEvents="none" />

                    <div className="overflow-x-auto relative z-10">
                        <table className="sessions-table w-full">
                            <thead>
                                <tr>
                                    <th>Identity</th>
                                    <th>Engine Core</th>
                                    <th>Link Status</th>
                                    <th>Active Skills</th>
                                    <th>Channels / Bridges</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {loading && agents.length === 0 ? (
                                    <tr><td colSpan={6} className="text-center py-8 opacity-50 text-[10px] font-mono tracking-widest">BOOTING_AGENT_ARRAY...</td></tr>
                                ) : agents.length === 0 ? (
                                    <tr><td colSpan={6} className="text-center py-8 opacity-50">No independent agents initialized.</td></tr>
                                ) : (
                                    agents.map(agent => (
                                        <tr
                                            key={agent.id}
                                            className="cursor-pointer hover:bg-glass-hover transition-colors"
                                            onClick={() => setSelectedAgentId(agent.id)}
                                        >
                                            <td className="font-medium text-text-primary flex items-center gap-2">
                                                {agent.name}
                                                {/* Client side dirty indicator mock wrapper injected natively */}
                                                <AgentDirtyIndicator agentId={agent.id} />
                                            </td>
                                            <td className="font-mono text-[10px] opacity-70">{agent.model}</td>
                                            <td>
                                                <span className={`px-2 py-0.5 rounded-full text-[9px] font-mono tracking-wider ${agent.status === 'READY' ? 'bg-status-good/10 text-status-good border border-status-good/20' : 'bg-glass-edge text-text-secondary'}`}>
                                                    {agent.status}
                                                </span>
                                            </td>
                                            <td className="text-center">{agent.active_skills || 0}</td>
                                            <td>
                                                <div className="flex items-center justify-center gap-1 opacity-70">
                                                    <Network size={12} /> {agent.channels || 0}
                                                </div>
                                            </td>
                                            <td>
                                                <button className="p-1.5 text-text-tertiary hover:text-accent bg-glass-pressed rounded-md transition-colors">
                                                    <Settings size={14} />
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

            </div>
        </div>
    );
};

export default AgentsPanel;
