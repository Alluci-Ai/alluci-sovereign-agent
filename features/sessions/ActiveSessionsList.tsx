import React, { useState } from 'react';
import { useStore } from '../../store/useStore';
import { adminService } from '../../adminService';
import {
    MessageSquare,
    Trash2,
    ArrowRight,
    Cpu,
    Globe,
    Zap,
    MoreHorizontal,
    RefreshCw
} from 'lucide-react';
import { DeleteSessionButton } from './DeleteSessionButton';

interface ActiveSessionsListProps {
    sessions: any[];
    loading: boolean;
    onRefresh: () => void;
}

export const ActiveSessionsList: React.FC<ActiveSessionsListProps> = ({
    sessions,
    loading,
    onRefresh
}) => {
    const { activeSessionKey, setActiveSessionKey, accessToken } = useStore();
    const [filter, setFilter] = useState<'all' | 'unlabeled'>('all');

    const filteredSessions = sessions.filter(s => {
        if (filter === 'unlabeled') return !s.label;
        return true;
    });

    const handleThinkingChange = (sessionKey: string, level: string) => {
        adminService.sendRPC('sessions.patch', {
            session_key: sessionKey,
            thinking_level: level
        });
    };

    return (
        <div className="bg-glass-1 border border-glass-edge rounded-xl overflow-hidden flex flex-col h-full">
            <div className="p-4 border-b border-glass-edge flex items-center justify-between bg-white/5">
                <div className="flex items-center gap-4">
                    <h3 className="glass-label text-xs tracking-widest uppercase">Active Sessions</h3>
                    <div className="flex bg-glass-pressed rounded-lg p-0.5">
                        <button
                            onClick={() => setFilter('all')}
                            className={`px-3 py-1 text-[10px] rounded-md transition-all ${filter === 'all' ? 'bg-accent text-black font-bold' : 'text-text-tertiary hover:text-text-secondary'}`}
                        >
                            Global
                        </button>
                        <button
                            onClick={() => setFilter('unlabeled')}
                            className={`px-3 py-1 text-[10px] rounded-md transition-all ${filter === 'unlabeled' ? 'bg-accent text-black font-bold' : 'text-text-tertiary hover:text-text-secondary'}`}
                        >
                            Unknown
                        </button>
                    </div>
                </div>

                <button
                    onClick={onRefresh}
                    className="p-2 hover:bg-glass-hover rounded-full transition-colors text-text-tertiary"
                    title="Sync Manifold"
                >
                    <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                </button>
            </div>

            <div className="overflow-auto flex-1 h-full">
                {loading && sessions.length === 0 ? (
                    <div className="flex flex-col items-center justify-center p-20 opacity-40 gap-4">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent"></div>
                        <p className="text-[10px] font-mono tracking-widest uppercase">Fetching_Session_Array...</p>
                    </div>
                ) : filteredSessions.length === 0 ? (
                    <div className="p-20 text-center opacity-30">
                        <MessageSquare size={40} className="mx-auto mb-4 opacity-20" />
                        <p className="text-sm">No active session footprints detected.</p>
                    </div>
                ) : (
                    <table className="sessions-table w-full">
                        <thead>
                            <tr>
                                <th>Session Key</th>
                                <th>Agent / Identity</th>
                                <th>Channel</th>
                                <th>Metrics</th>
                                <th>Thinking</th>
                                <th className="text-right">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredSessions.map(session => (
                                <tr
                                    key={session.session_key}
                                    className={`group cursor-pointer hover:bg-glass-hover transition-colors ${activeSessionKey === session.session_key ? 'bg-accent/[0.03] border-l-2 border-l-accent' : ''}`}
                                    onClick={() => setActiveSessionKey(session.session_key)}
                                >
                                    <td>
                                        <div className="flex items-center gap-2">
                                            <span className="font-mono text-[10px] bg-glass-pressed px-1.5 py-0.5 rounded text-accent/80">
                                                {(session.session_key || "UNKNOWN").slice(0, 8)}
                                            </span>
                                        </div>
                                    </td>
                                    <td>
                                        <div className="flex flex-col">
                                            <span className="text-[13px] font-medium text-text-primary capitalize">
                                                {session.agent_name || session.label || "Sovereign Root"}
                                            </span>
                                            <span className="text-[10px] opacity-40 font-mono uppercase tracking-tighter">
                                                {session.models?.[0] || "AUTO_ROUTER"}
                                            </span>
                                        </div>
                                    </td>
                                    <td>
                                        <div className="flex items-center gap-2">
                                            <div className="p-1.5 bg-glass-pressed rounded-md text-text-tertiary">
                                                <Globe size={12} />
                                            </div>
                                            <div className="flex flex-col">
                                                <span className="text-[11px] font-medium capitalize">{session.channel_type || "Internal"}</span>
                                                <span className="text-[9px] opacity-40">{session.channel_label || "Direct Gateway"}</span>
                                            </div>
                                        </div>
                                    </td>
                                    <td>
                                        <div className="flex items-center gap-3">
                                            <div className="flex flex-col">
                                                <span className="text-[10px] font-mono text-text-primary">{(session.total_input + session.total_output).toLocaleString()}</span>
                                                <span className="text-[8px] opacity-30 uppercase">Tokens</span>
                                            </div>
                                            <div className="h-6 w-[1px] bg-glass-edge"></div>
                                            <div className="flex flex-col">
                                                <span className="text-[10px] font-mono text-status-good">${(session.total_cost || 0).toFixed(4)}</span>
                                                <span className="text-[8px] opacity-30 uppercase">Expenditure</span>
                                            </div>
                                        </div>
                                    </td>
                                    <td>
                                        <select
                                            value={session.thinking_level || "MEDIUM"}
                                            onChange={(e) => handleThinkingChange(session.session_key, e.target.value)}
                                            onClick={(e) => e.stopPropagation()}
                                            className="bg-transparent border-none text-[10px] font-bold text-accent p-0 cursor-pointer focus:ring-0"
                                        >
                                            <option value="LOW">FAST</option>
                                            <option value="MEDIUM">BALANCED</option>
                                            <option value="HIGH">ANALYTICAL</option>
                                        </select>
                                    </td>
                                    <td className="text-right">
                                        <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button
                                                className="p-1.5 hover:bg-glass-pressed rounded-md text-text-tertiary hover:text-accent transition-colors"
                                                onClick={(e) => { e.stopPropagation(); setActiveSessionKey(session.session_key); }}
                                                title="Switch to Session"
                                            >
                                                <ArrowRight size={14} />
                                            </button>
                                            <DeleteSessionButton sessionKey={session.session_key} />
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>

            <div className="p-3 border-t border-glass-edge bg-black/10 flex items-center justify-between">
                <p className="text-[9px] font-mono opacity-30 uppercase tracking-widest">
                    Active_Manifold_Cluster: {filteredSessions.length} sessions detected
                </p>
                <div className="flex items-center gap-2">
                    <Zap size={10} className="text-accent animate-pulse" />
                    <span className="text-[9px] opacity-30">Real-time Presence Active</span>
                </div>
            </div>
        </div>
    );
};

export default ActiveSessionsList;
