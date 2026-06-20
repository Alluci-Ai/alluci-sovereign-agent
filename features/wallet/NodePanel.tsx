import React, { useState, useEffect } from 'react';
import { Cpu, HardDrive, Share2, Power, RefreshCw, Terminal as TerminalIcon, Shield } from 'lucide-react';
import { useStore } from '../../store/useStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

interface NodeStatus {
    active: boolean;
    pid: number | null;
    sync: {
        height: number;
        longestchain: number;
        percent: number;
    };
    directories: {
        bin: string;
        data: string;
    };
}

export const NodePanel: React.FC = () => {
    const { accessToken, walletMode } = useStore();
    const [status, setStatus] = useState<NodeStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState<string | null>(null);

    const fetchStatus = async () => {
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/wallet/node/status`, {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });
            if (res.ok) {
                const data = await res.json();
                setStatus(data);
            }
        } catch (err) {
            console.error("Failed to fetch node status", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStatus();
        const int = setInterval(fetchStatus, 5000);
        return () => clearInterval(int);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleAction = async (action: string) => {
        setActionLoading(action);
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/wallet/node/action`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ action })
            });
            if (res.ok) {
                fetchStatus();
            }
        } catch (err) {
            console.error("Node action failed", err);
        } finally {
            setActionLoading(null);
        }
    };

    if (walletMode === 'lite') {
        return (
            <div className="glass-panel p-12 flex flex-col items-center justify-center text-center space-y-6 min-h-[400px]">
                <div className="w-20 h-20 rounded-3xl bg-white/[0.03] border border-white/10 flex items-center justify-center shadow-inner">
                    <Shield className="text-text-muted" size={40} />
                </div>
                <div className="space-y-2">
                    <h3 className="text-2xl font-semibold text-text-primary tracking-tight">Lite Mode Active</h3>
                    <p className="text-text-tertiary max-w-sm mx-auto">
                        Node management is only available in Sovereign Mode. Upgrade to manage a local daemon and enjoy true decentralization.
                    </p>
                </div>
            </div>
        );
    }

    if (loading && !status) {
        return (
            <div className="flex-1 flex items-center justify-center h-full">
                <RefreshCw className="animate-spin text-accent" />
            </div>
        );
    }

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            {/* Node Hero Section */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 glass-panel p-8 relative overflow-hidden group border-white/5 bg-white/[0.02]">
                    <div className="absolute inset-0 bg-gradient-to-br from-accent/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
                    <div className="flex items-start justify-between">
                        <div className="space-y-4">
                            <div className="flex items-center gap-3">
                                <div className={`p-2.5 rounded-xl ${status?.active ? 'bg-status-success/10 text-status-success' : 'bg-status-error/10 text-status-error'} border border-white/5 shadow-inner`}>
                                    <Power size={20} />
                                </div>
                                <div>
                                    <h3 className="text-xl font-bold text-text-primary tracking-tight">verusd Local Daemon</h3>
                                    <p className="text-[10px] font-bold text-text-tertiary uppercase tracking-widest leading-none mt-1">
                                        {status?.active ? `Running (PID: ${status.pid})` : 'Daemon Offline'}
                                    </p>
                                </div>
                            </div>

                            <div className="flex items-center gap-4 pt-4">
                                <button
                                    onClick={() => handleAction(status?.active ? 'stop' : 'start')}
                                    disabled={!!actionLoading}
                                    className={`glass-btn text-[11px] font-bold px-6 py-2.5 uppercase tracking-widest transition-all duration-300 flex items-center gap-2 ${status?.active ? 'border-status-error/30 text-status-error hover:bg-status-error/5' : 'border-status-success/30 text-status-success hover:bg-status-success/5'}`}
                                >
                                    {actionLoading === 'start' || actionLoading === 'stop' ? <RefreshCw size={14} className="animate-spin" /> : <Power size={14} />}
                                    {status?.active ? 'Stop Node' : 'Start Node'}
                                </button>
                                <button
                                    onClick={() => handleAction('restart')}
                                    disabled={!!actionLoading || !status?.active}
                                    className="glass-btn text-[11px] font-bold px-6 py-2.5 uppercase tracking-widest border-white/10 text-text-tertiary hover:border-accent/30 hover:text-accent transition-all duration-300 flex items-center gap-2"
                                >
                                    {actionLoading === 'restart' ? <RefreshCw size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                                    Restart
                                </button>
                            </div>
                        </div>

                        <div className="text-right space-y-1">
                            <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-widest block mb-1 font-mono">Blockchain Progress</span>
                            <div className="text-4xl font-bold tracking-tighter text-text-primary tabular-nums">
                                {status?.sync.percent.toFixed(2)}%
                            </div>
                        </div>
                    </div>

                    <div className="mt-8 space-y-2">
                        <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden border border-white/5 shadow-inner p-[1px]">
                            <div
                                className="h-full bg-gradient-to-r from-accent via-indigo-500 to-accent bg-[length:200%_auto] animate-shimmer rounded-full transition-all duration-1000 ease-out"
                                style={{ width: `${status?.sync.percent || 0}%` }}
                            />
                        </div>
                        <div className="flex justify-between text-[10px] font-bold text-text-tertiary uppercase tracking-tighter">
                            <span>Block Height: {status?.sync.height.toLocaleString()}</span>
                            <span>Network High: {status?.sync.longestchain.toLocaleString()}</span>
                        </div>
                    </div>
                </div>

                <div className="glass-panel p-8 space-y-6 flex flex-col justify-between border-white/5 bg-white/[0.02]">
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-widest">Storage</span>
                            <HardDrive size={14} className="text-text-muted" />
                        </div>
                        <div className="p-3 rounded-lg bg-black/20 border border-white/5 font-mono text-[9px] text-text-tertiary break-all space-y-2">
                            <div>
                                <span className="text-accent/60">BIN:</span> {status?.directories.bin}
                            </div>
                            <div>
                                <span className="text-indigo-400/60">DATA:</span> {status?.directories.data}
                            </div>
                        </div>
                    </div>
                    <div className="pt-4 border-t border-white/5">
                        <div className="flex items-center justify-between text-[11px] mb-3">
                            <span className="text-text-tertiary font-bold uppercase tracking-widest">Network Mode</span>
                            <span className="text-accent font-bold px-2 py-0.5 rounded bg-accent/10 border border-accent/20 tracking-tighter uppercase leading-none">Mainnet</span>
                        </div>
                        <p className="text-[10px] text-text-muted italic leading-relaxed">
                            Daemon running with -txindex and -addressindex enabled for full sovereign functionality.
                        </p>
                    </div>
                </div>
            </div>

            {/* Terminal Interface */}
            <div className="glass-panel border-white/5 bg-black/40 overflow-hidden group">
                <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-white/[0.02]">
                    <div className="flex items-center gap-3">
                        <div className="p-1.5 rounded-lg bg-white/5 text-text-muted group-hover:text-accent transition-colors">
                            <TerminalIcon size={16} />
                        </div>
                        <h4 className="text-sm font-bold text-text-secondary uppercase tracking-widest">Sovereign Terminal</h4>
                    </div>
                    <div className="flex items-center gap-4 text-[10px] font-mono text-text-tertiary">
                        <span className="flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-status-success" />
                            CLI STDOUT STREAMING
                        </span>
                    </div>
                </div>
                <div className="p-6 bg-black/60 font-mono text-sm min-h-[300px] flex flex-col justify-end space-y-2 text-text-muted relative">
                    <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_120%,rgba(56,189,248,0.05),transparent)] opacity-50 pointer-events-none" />

                    <div className="space-y-1.5 relative z-10">
                        <div className="text-accent/60 flex gap-2">
                            <span>$</span>
                            <span className="text-text-secondary">verusd -datadir={status?.directories.data} -conf=VRSC.conf</span>
                        </div>
                        <div className="text-[12px] text-text-muted/40 leading-relaxed font-light">
                            [Node] Initialization complete. Loading block index...
                            [Node] Address index enabled. Reindexing not required.
                            [Node] Verus P2P listening on port 27485
                            [Node] RPC server started on port 27486
                        </div>
                        <div className="text-status-success/80 flex gap-2 pt-2">
                            <span>❯</span>
                            <span className="animate-pulse">_</span>
                        </div>
                    </div>

                    <div className="absolute bottom-6 right-6 opacity-20 group-hover:opacity-100 transition-opacity">
                        <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-[0.2em]">Interactivity Coming Soon</span>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="glass-panel p-6 border-white/5 bg-white/[0.01]">
                    <div className="flex items-center gap-3 mb-4">
                        <Cpu className="text-text-muted" size={18} />
                        <h4 className="text-[11px] font-bold text-text-tertiary uppercase tracking-widest">Processor Intensity</h4>
                    </div>
                    <div className="space-y-4">
                        <div className="flex justify-between items-end">
                            <span className="text-xs text-text-secondary">Thread Utilization</span>
                            <span className="text-xl font-bold text-text-primary">4 / 12</span>
                        </div>
                        <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                            <div className="h-full bg-accent w-1/3" />
                        </div>
                    </div>
                </div>
                <div className="glass-panel p-6 border-white/5 bg-white/[0.01]">
                    <div className="flex items-center gap-3 mb-4">
                        <Share2 className="text-text-muted" size={18} />
                        <h4 className="text-[11px] font-bold text-text-tertiary uppercase tracking-widest">Peer Connectivity</h4>
                    </div>
                    <div className="space-y-4">
                        <div className="flex justify-between items-end">
                            <span className="text-xs text-text-secondary">Inbound / Outbound</span>
                            <span className="text-xl font-bold text-text-primary">8 / 26</span>
                        </div>
                        <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                            <div className="h-full bg-indigo-500 w-[60%]" />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
