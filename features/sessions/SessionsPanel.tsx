import React, { useEffect, useState } from 'react';
import { useStore } from '../../store/useStore';
import { Plus, LayoutGrid, Settings2, BarChart3 } from 'lucide-react';
import { SessionOverrides } from './SessionOverrides';
import { SessionCostDisplay } from './SessionCostDisplay';
import { ActiveSessionsList } from './ActiveSessionsList';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

/**
 * SessionsPanel — Refactored Sessions Manifold.
 * Implements a triple-panel Liquid Glass architecture for high-density session management.
 */
export const SessionsPanel: React.FC = () => {
    const { sessions, setSessions, setActiveSessionKey, accessToken } = useStore();
    const [loading, setLoading] = useState(false);

    const fetchSessions = async () => {
        if (loading) return;
        setLoading(true);

        const controller = new AbortController();
        const tId = setTimeout(() => controller.abort(), 5000); // 5s timeout

        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/sessions`, {
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include',
                signal: controller.signal
            });
            clearTimeout(tId);

            if (res.ok) {
                const data = await res.json();
                setSessions(Array.isArray(data.sessions) ? data.sessions : []);
            } else {
                // If backend is up but sessions endpoint fails, still clear loading
                if (sessions.length === 0) setSessions([]);
            }
        } catch (err: any) {
            console.warn('[SessionsPanel] Manifold sync interrupted:', err.message);
            // PROACTIVE FALLBACK: If we have no sessions and the server is down,
            // we'll inject a helpful placeholder to break the loading loop.
            if (sessions.length === 0) {
                // We keep it empty but set it to [] to trigger "No Footprints Found"
                setSessions([]);
            }
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSessions();
        const interval = setInterval(() => fetchSessions(), 30000);
        return () => clearInterval(interval);
    }, [accessToken]);

    const handleNewSession = () => {
        const newKey = crypto.randomUUID();
        setActiveSessionKey(newKey);
        // Add to local state immediately for UX
        const stub = {
            session_key: newKey,
            agent_name: "New Sovereign Session",
            channel_type: "internal",
            total_input: 0,
            total_output: 0,
            total_cost: 0,
            models: ["auto"],
            thinking_level: "MEDIUM"
        };
        setSessions([stub, ...sessions]);
    };

    return (
        <div className="inline-panel-wrapper overflow-hidden bg-transparent">
            <div className="max-w-[1600px] mx-auto w-full h-full flex flex-col gap-6 lg:p-6 p-4">

                {/* Header Section */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-glass-edge pb-6">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-accent/10 border border-accent/20 rounded-lg text-accent">
                            <LayoutGrid size={20} />
                        </div>
                        <div className="flex flex-col">
                            <h2 className="text-xl font-medium tracking-tight text-text-primary">Sessions Manifold</h2>
                            <p className="text-[10px] opacity-40 font-mono tracking-widest uppercase">Cognitive_Session_Coordinator</p>
                        </div>
                    </div>

                    <button
                        onClick={handleNewSession}
                        className="glass-btn flex items-center gap-2 group hover:border-accent/50 transition-all font-medium"
                    >
                        <Plus size={16} className="text-accent group-hover:scale-125 transition-transform" />
                        Initialize New Protocol
                    </button>
                </div>

                {/* Triple Panel Layout */}
                <div className="flex-1 flex flex-col lg:flex-row gap-6 min-h-0">

                    {/* Left Sidebar (Metrics & Controls) */}
                    <div className="w-full lg:w-[320px] flex flex-col gap-6 shrink-0 h-full overflow-y-auto pr-2 custom-scrollbar">
                        <div className="flex flex-col gap-4">
                            <div className="flex items-center gap-2 opacity-50 px-1">
                                <BarChart3 size={12} />
                                <span className="text-[10px] font-bold uppercase tracking-wider">Session Insight</span>
                            </div>
                            <SessionCostDisplay />
                        </div>

                        <div className="flex flex-col gap-4">
                            <div className="flex items-center gap-2 opacity-50 px-1">
                                <Settings2 size={12} />
                                <span className="text-[10px] font-bold uppercase tracking-wider">Constraint Matrix</span>
                            </div>
                            <SessionOverrides />
                        </div>

                        <div className="mt-auto p-4 bg-glass-pressed rounded-xl border border-glass-edge">
                            <p className="text-[10px] leading-relaxed text-text-tertiary">
                                <span className="text-accent font-bold">PRO TIP:</span> Use the thinking depth envelope to balance execution speed versus cognitive precision on a per-session basis.
                            </p>
                        </div>
                    </div>

                    {/* Main Content Area (Active Sessions List) */}
                    <div className="flex-1 min-w-0 h-full">
                        <ActiveSessionsList
                            sessions={sessions}
                            loading={loading}
                            onRefresh={fetchSessions}
                        />
                    </div>

                </div>
            </div>
        </div>
    );
};

export default SessionsPanel;
