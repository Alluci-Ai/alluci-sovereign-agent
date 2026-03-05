import React, { useState, useEffect } from 'react';
import { WalletOverview } from './WalletOverview';
import { WalletSendReceive } from './WalletSendReceive';
import { WalletTransactions } from './WalletTransactions';
import { WalletMining } from './WalletMining';
import { NodePanel } from './NodePanel';
import { useStore } from '../../store/useStore';
import { LayoutDashboard, Server, History, Shield } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

interface DashboardData {
    connected: boolean;
    identity?: {
        name: string;
        identityaddress: string;
        status: string;
    };
    total_vrsc: number;
    unconfirmed: number;
    balances: any[];
    mining?: {
        generating: boolean;
        staking: boolean;
        hashrate: number;
        local_hashrate: number;
    };
    recent_transactions: any[];
    pbaas_chains: string[];
}

export const WalletPanel: React.FC = () => {
    const { accessToken, walletMode, setWalletMode, walletStatus, setWalletStatus } = useStore();
    const [dashboard, setDashboard] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'dashboard' | 'node'>('dashboard');

    const fetchDashboard = async () => {
        try {
            const res = await fetch(`${DAEMON_URL}/api/wallet/dashboard`, {
                headers: { 'Authorization': `Bearer ${accessToken}` }
            });
            if (!res.ok) throw new Error('Failed to fetch wallet dashboard data');
            const data = await res.json();
            setDashboard(data);
            setWalletStatus(data.connected ? 'synced' : 'offline');
            setError(null);
        } catch (err: any) {
            setError(err.message || "Failed to load wallet state");
            setWalletStatus('offline');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDashboard();
        const int = setInterval(fetchDashboard, 15000);
        return () => clearInterval(int);
    }, []);

    const handleRefresh = () => {
        setLoading(true);
        fetchDashboard();
    };

    const toggleSovereignMode = async () => {
        const nextMode = walletMode === 'lite' ? 'sovereign' : 'lite';
        if (nextMode === 'sovereign') {
            if (window.confirm("Upgrade to Sovereign Mode? This will download and manage a local Verus node (verusd). Proceed?")) {
                setWalletMode('sovereign');
                setActiveTab('node');
                // Trigger provisioning and start in background
                try {
                    await fetch(`${DAEMON_URL}/api/wallet/node/action`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${accessToken}`,
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ action: 'start' })
                    });
                } catch (err) {
                    console.error("Failed to auto-start node", err);
                }
            }
        } else {
            setWalletMode('lite');
            setActiveTab('dashboard');
        }
    };

    if (loading && !dashboard) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center h-full text-text-muted space-y-4">
                <div className="w-8 h-8 rounded-full border-t-2 border-r-2 border-b-2 border-accent/20 border-l-2 border-l-accent animate-spin" />
                <p>Syncing wallet with Verus network...</p>
            </div>
        );
    }

    return (
        <div className="flex-1 overflow-y-auto w-full h-full pb-12 glass-container">
            <div className="top-bar sticky top-0 z-20 px-6 py-4 border-b border-white/5 bg-surface-base/40 backdrop-blur-xl flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${walletMode === 'sovereign' ? 'from-accent to-indigo-600' : 'from-indigo-400 to-indigo-600'} flex items-center justify-center shadow-lg shadow-indigo-500/20`}>
                        <div className="text-white">
                            {walletMode === 'sovereign' ? (
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10" /></svg>
                            ) : (
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m5 11 4-7" /><path d="m19 11-4-7" /><path d="M22 11a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2 2 2 0 0 0 2 2h16a2 2 0 0 0 2-2Z" /><path d="M4 13v6a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-6" /></svg>
                            )}
                        </div>
                    </div>
                    <div>
                        <h2 className="text-xl font-semibold text-text-primary tracking-tight flex items-center gap-2">
                            Sovereign Wallet
                            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${walletMode === 'sovereign' ? 'bg-accent/20 text-accent border border-accent/30' : 'bg-white/10 text-white/60 border border-white/10'}`}>
                                {walletMode}
                            </span>
                        </h2>
                        <p className="text-xs text-text-tertiary">PBaaS Multi-Currency Infrastructure</p>
                    </div>
                </div>

                <div className="flex items-center gap-6">
                    <div className="flex flex-col items-end gap-1">
                        <div className="flex items-center gap-2">
                            <div className={`w-2 h-2 rounded-full ${walletStatus === 'synced' ? 'bg-status-success animate-pulse shadow-[0_0_8px_rgba(56,189,248,0.5)]' : 'bg-status-error shadow-[0_0_8px_rgba(239,68,68,0.5)]'}`} />
                            <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-widest leading-none">
                                {walletStatus === 'synced' ? 'System Online' : 'System Offline'}
                            </span>
                        </div>
                        <span className="text-[9px] font-mono text-text-muted uppercase tracking-tighter">
                            {walletMode === 'sovereign' ? 'Native Daemon Active' : 'Connected to Public RPC'}
                        </span>
                    </div>

                    <button
                        onClick={toggleSovereignMode}
                        className={`glass-btn text-[11px] font-bold px-4 py-2 uppercase tracking-wider transition-all duration-500 ${walletMode === 'sovereign' ? 'border-status-success/40 text-status-success bg-status-success/5 shadow-inner' : 'border-white/10 text-text-secondary hover:border-accent/40 hover:text-accent'}`}
                    >
                        {walletMode === 'lite' ? 'Go Sovereign' : 'Sovereign Active'}
                    </button>
                </div>
            </div>

            <div className="px-8 pt-4">
                <div className="flex items-center gap-1 bg-white/5 p-1 rounded-xl w-fit border border-white/5 backdrop-blur-md">
                    <button
                        onClick={() => setActiveTab('dashboard')}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all duration-300 ${activeTab === 'dashboard' ? 'bg-accent text-white shadow-lg shadow-accent/20' : 'hover:bg-white/5 text-text-tertiary'}`}
                    >
                        <LayoutDashboard size={14} />
                        Dashboard
                    </button>
                    <button
                        onClick={() => setActiveTab('node')}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all duration-300 ${activeTab === 'node' ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20' : 'hover:bg-white/5 text-text-tertiary'}`}
                    >
                        <Server size={14} />
                        Node Manager
                    </button>
                </div>
            </div>

            <div className="p-8 space-y-8 max-w-[1400px] mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
                {activeTab === 'dashboard' ? (
                    <>
                        <WalletOverview data={dashboard} />

                        <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                            <WalletSendReceive onTransactionComplete={handleRefresh} />
                            <WalletMining
                                mining={dashboard?.mining}
                                chains={dashboard?.pbaas_chains || []}
                                onStateChange={handleRefresh}
                            />
                        </div>

                        <WalletTransactions recent={dashboard?.recent_transactions} />
                    </>
                ) : (
                    <NodePanel />
                )}
            </div>
        </div>
    );
};
