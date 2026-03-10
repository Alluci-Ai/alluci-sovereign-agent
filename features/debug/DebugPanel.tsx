import React, { useState, useEffect } from 'react';
import { useStore } from '../../store/useStore';
import { adminService } from '../../adminService';
import { useTranslation } from 'react-i18next';
import { Terminal, Shield, Activity, Code, Server, CheckCircle, AlertTriangle, XCircle, LayoutGrid } from 'lucide-react';
import { SystemHealthCard } from './SystemHealthCard';
import { RpcConsole } from '../system/RpcConsole';

export const DebugPanel: React.FC = () => {
    const { accessToken, activeView } = useStore();
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState<'events' | 'rpc' | 'security' | 'health'>('events');

    // Event Log State
    const [events, setEvents] = useState<{ id: string; timestamp: Date; method: string; payload: any; expanded: boolean }[]>([]);

    // Security Audit State
    const [auditLedger, setAuditLedger] = useState<any[]>([]);
    const [stats, setStats] = useState<any>(null);

    useEffect(() => {
        // Event Listener hook
        const handleWSEvent = (method: string, params: any) => {
            setEvents(prev => {
                const newEv = { id: crypto.randomUUID(), timestamp: new Date(), method, payload: params, expanded: false };
                const next = [newEv, ...prev];
                return next.slice(0, 500); // Keep last 500 max
            });
        };

        adminService.addListener(handleWSEvent);
        return () => {
            // Memory cleanup (Assuming adminService has removeListener or similar if supported, otherwise it just runs)
        };
    }, []);

    useEffect(() => {
        // Fetch Security Audit if we're on that tab
        if (activeTab === 'security') {
            const fetchStatus = async () => {
                try {
                    const res = await fetch(`${import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000'}/status`, {
                        headers: { 'Authorization': `Bearer ${accessToken}` },
                        credentials: 'include'
                    });
                    if (res.ok) {
                        const data = await res.json();
                        setStats(data.security_audit); // Contains summary
                        // Usually audit ledger array is returned somewhere else or here, mock it falling back to summary for now
                        setAuditLedger(data.security_audit?.full_ledger || []);
                    }
                } catch (err) {
                    console.error('Failed fetching security status', err);
                }
            };
            fetchStatus();
        }
    }, [activeTab, accessToken]);

    const toggleEventPayload = (id: string) => {
        setEvents(prev => prev.map(ev => ev.id === id ? { ...ev, expanded: !ev.expanded } : ev));
    };

    return (
        <div className="inline-panel-wrapper overflow-auto">
            <div className="max-w-7xl mx-auto w-full flex flex-col gap-6 lg:p-6 p-4 h-full">

                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-glass-edge pb-4">
                    <div className="flex items-center gap-3">
                        <Terminal size={20} className="text-accent" />
                        <h2 className="text-xl font-medium tracking-tight text-text-primary">{t('debug.title')}</h2>
                    </div>

                    <div className="flex bg-glass-1 border border-glass-edge p-1 rounded-xl">
                        <button
                            onClick={() => setActiveTab('events')}
                            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs transition-all ${activeTab === 'events' ? 'bg-glass-pressed text-accent shadow-sm' : 'text-text-tertiary hover:text-text-primary'}`}
                        >
                            <LayoutGrid size={14} /> Event Log
                        </button>
                        <button
                            onClick={() => setActiveTab('rpc')}
                            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs transition-all ${activeTab === 'rpc' ? 'bg-glass-pressed text-accent shadow-sm' : 'text-text-tertiary hover:text-text-primary'}`}
                        >
                            <Code size={14} /> RPC Console
                        </button>
                        <button
                            onClick={() => setActiveTab('security')}
                            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs transition-all ${activeTab === 'security' ? 'bg-glass-pressed text-accent shadow-sm' : 'text-text-tertiary hover:text-text-primary'}`}
                        >
                            <Shield size={14} /> Security Audit
                        </button>
                        <button
                            onClick={() => setActiveTab('health')}
                            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs transition-all ${activeTab === 'health' ? 'bg-glass-pressed text-accent shadow-sm' : 'text-text-tertiary hover:text-text-primary'}`}
                        >
                            <Server size={14} /> Health Matrix
                        </button>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto w-full h-full min-h-[500px]">
                    {activeTab === 'events' && (
                        <div className="bg-glass-1 border border-glass-edge rounded-xl p-4 flex flex-col gap-2 min-h-full">
                            {events.length === 0 ? (
                                <div className="flex items-center justify-center opacity-40 text-xs font-mono h-32 tracking-widest">{t('debug.awaiting_data')}</div>
                            ) : events.map(ev => (
                                <div key={ev.id} className="border border-white/5 bg-glass-2 rounded-lg p-3 hover:bg-glass-hover transition-colors font-mono text-[11px] flex flex-col gap-2">
                                    <div className="flex items-center justify-between cursor-pointer" onClick={() => toggleEventPayload(ev.id)}>
                                        <div className="flex items-center gap-4">
                                            <span className="opacity-50">{ev.timestamp.toLocaleTimeString()}</span>
                                            <span className="text-accent font-bold tracking-wider">{ev.method}</span>
                                        </div>
                                        <span className="text-[9px] opacity-40 glass-label">{ev.expanded ? 'COLLAPSE' : 'EXPAND'}</span>
                                    </div>
                                    {ev.expanded && (
                                        <pre className="bg-black/50 p-2 rounded-lg overflow-x-auto text-[10px] text-text-secondary mt-1 border border-white/5 opacity-80">
                                            {JSON.stringify(ev.payload, null, 2)}
                                        </pre>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}

                    {activeTab === 'rpc' && (
                        <div className="relative w-full h-[600px] border border-glass-edge bg-glass-1 rounded-xl overflow-hidden flex items-center justify-center">
                            <span className="absolute glass-label text-[10px] opacity-40 top-4 left-4 z-0">RPC FRAMEWORK WRAPPER</span>
                            <RpcConsole />
                        </div>
                    )}

                    {activeTab === 'security' && (
                        <div className="bg-glass-1 border border-glass-edge rounded-xl p-5 flex flex-col gap-4">
                            <h3 className="glass-label text-sm tracking-widest flex items-center gap-2"><Shield size={16} className="text-status-good" /> SECURITY VAULT AUDIT MATRIX</h3>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                                <div className="border border-glass-edge bg-glass-2 rounded-lg p-4">
                                    <div className="glass-label text-[10px] opacity-50 mb-1">Total Ledger Events</div>
                                    <div className="font-mono text-xl">{stats?.total_events ?? '—'}</div>
                                </div>
                                <div className="border border-[var(--status-error-rgb)]/20 bg-glass-2 rounded-lg p-4 relative overflow-hidden">
                                    <AlertTriangle size={60} className="absolute -right-2 -bottom-2 opacity-10 text-status-error" />
                                    <div className="glass-label text-[10px] opacity-50 mb-1">Last Violation Hash</div>
                                    <div className="font-mono text-[10px] text-status-error tracking-wider">{stats?.last_violation || 'NONE_DETECTED'}</div>
                                </div>
                                <div className="border border-[var(--status-good-rgb)]/20 bg-glass-2 rounded-lg p-4 relative overflow-hidden">
                                    <CheckCircle size={60} className="absolute -right-2 -bottom-2 opacity-10 text-status-good" />
                                    <div className="glass-label text-[10px] opacity-50 mb-1">Manifold Integrity Matrix Hash</div>
                                    <div className="font-mono text-[10px] text-status-good truncate" title={stats?.integrity_hash}>{stats?.integrity_hash ?? '0x00...'}</div>
                                </div>
                            </div>

                            {auditLedger.length > 0 ? (
                                <table className="w-full text-left text-xs">
                                    <thead className="glass-label opacity-60 bg-glass-2">
                                        <tr><th className="p-2">Timestamp</th><th className="p-2">Event Code</th><th className="p-2">Payload Details</th></tr>
                                    </thead>
                                    <tbody>
                                        {auditLedger.map((l, i) => (
                                            <tr key={i} className="border-b border-glass-edge">
                                                <td className="p-2 font-mono">{l.timestamp || '—'}</td>
                                                <td className="p-2 text-status-error">{l.event}</td>
                                                <td className="p-2">{JSON.stringify(l)}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            ) : (
                                <div className="opacity-50 text-xs font-mono text-center p-10 tracking-widest">
                                    LEDGER_ARRAY_EMPTY_OR_ARCHIVED
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'health' && (
                        <div className="animate-in fade-in zoom-in-95 duration-300 w-full max-w-xl">
                            <SystemHealthCard />
                        </div>
                    )}
                </div>

            </div>
        </div>
    );
};

export default DebugPanel;
