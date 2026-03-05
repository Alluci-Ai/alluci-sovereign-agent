import React, { useState } from 'react';
import { Pickaxe, TrendingUp, Cpu, Server, AlertTriangle, Layers, Zap } from 'lucide-react';
import { useStore } from '../../store/useStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

interface WalletMiningProps {
    mining: any;
    chains: string[];
    onStateChange: () => void;
}

export const WalletMining: React.FC<WalletMiningProps> = ({ mining, chains, onStateChange }) => {
    const { accessToken } = useStore();
    const [loading, setLoading] = useState(false);
    const [threads, setThreads] = useState<number>(4);
    const [selectedChains, setSelectedChains] = useState<string[]>(['VRSC']);

    const toggleMining = async (action: 'mining/start' | 'mining/stop', mode: 'mine' | 'stake' = 'mine') => {
        setLoading(true);
        try {
            const body = action === 'mining/start' ? JSON.stringify({
                mode,
                threads: mode === 'mine' ? threads : 0,
                chains: selectedChains
            }) : undefined;

            const res = await fetch(`${DAEMON_URL}/api/wallet/${action}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`
                },
                body
            });
            if (!res.ok) throw new Error('Failed to toggle mining state');
            onStateChange();
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const toggleChain = (chain: string) => {
        if (selectedChains.includes(chain)) {
            if (selectedChains.length > 1) {
                setSelectedChains(selectedChains.filter(c => c !== chain));
            }
        } else {
            setSelectedChains([...selectedChains, chain]);
        }
    };

    const isMining = mining?.generating;
    const isStaking = mining?.staking;
    const isActive = isMining || isStaking;

    return (
        <div className="glass-panel p-6 flex flex-col h-[400px]">
            <div className="flex items-center justify-between border-b border-border/40 pb-4 mb-5">
                <div>
                    <h3 className="font-medium text-text-primary flex items-center gap-2">
                        <Pickaxe size={18} className={isActive ? "text-accent" : "text-text-muted"} />
                        <span className={isActive ? "text-accent" : ""}>Consensus Engine</span>
                    </h3>
                    <p className="text-[10px] text-text-tertiary mt-1 uppercase tracking-widest font-semibold flex items-center gap-2">
                        Proof of Power
                        <span className="w-1 h-1 rounded-full bg-border" />
                        50% PoW / 50% PoS
                    </p>
                </div>
                {isActive && (
                    <div className="flex items-center gap-3">
                        <div className="text-[10px] font-mono text-accent animate-pulse px-2 py-0.5 bg-accent/10 rounded border border-accent/20">
                            EXTRACTING VALUE...
                        </div>
                        <div className="flex h-3 w-3 relative">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-3 w-3 bg-accent border-[2px] border-surface-base"></span>
                        </div>
                    </div>
                )}
            </div>

            <div className="flex-1 overflow-y-auto pr-1 space-y-5">
                {/* Stats Row */}
                <div className="grid grid-cols-2 gap-4">
                    <div className="bg-surface-base/40 border border-border/30 rounded-lg p-3 group hover:border-accent/30 transition-colors">
                        <span className="text-[10px] font-medium uppercase tracking-wider text-text-tertiary mb-1 flex items-center gap-1.5"><TrendingUp size={12} /> Network Difficulty</span>
                        <div className="text-lg font-mono tracking-tight text-text-primary">
                            {(mining?.difficulty || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </div>
                    </div>
                    <div className="bg-surface-base/40 border border-border/30 rounded-lg p-3 group hover:border-accent/30 transition-colors">
                        <span className="text-[10px] font-medium uppercase tracking-wider text-text-tertiary mb-1 flex items-center gap-1.5"><Cpu size={12} /> Combined Hashrate</span>
                        <div className="text-lg font-mono tracking-tight text-accent">
                            {((mining?.local_hashrate || 0) / 1000000).toFixed(2)} <span className="text-xs text-text-secondary">MH/s</span>
                        </div>
                    </div>
                </div>

                {/* PBaaS Multi-Chain Selector */}
                <div className="space-y-2">
                    <label className="text-[10px] font-bold text-text-tertiary uppercase tracking-wider flex items-center gap-2">
                        <Layers size={12} /> PBaaS Chain Merge-Mining ({selectedChains.length}/22)
                    </label>
                    <div className="flex flex-wrap gap-2">
                        {chains.map(chain => (
                            <button
                                key={chain}
                                onClick={() => toggleChain(chain)}
                                disabled={isActive && isMining}
                                className={`px-2.5 py-1 rounded text-[10px] font-bold transition-all border ${selectedChains.includes(chain)
                                        ? 'bg-accent/20 border-accent/40 text-accent'
                                        : 'bg-surface-base border-border/40 text-text-tertiary hover:border-text-muted'
                                    }`}
                            >
                                {chain}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Thread Controls */}
                <div className="glass-panel border-accent/20 bg-accent/5 p-4 rounded-lg flex flex-col gap-3">
                    <div className="flex items-center justify-between">
                        <label className="text-xs font-semibold text-text-secondary flex items-center gap-2">
                            <Server size={14} className="text-accent" /> Parallel Processors
                        </label>
                        <span className="text-[10px] font-mono text-accent bg-accent/10 px-2 py-0.5 rounded border border-accent/20">{threads} {threads === 1 ? 'CORE' : 'CORES'}</span>
                    </div>
                    <input
                        type="range"
                        min="1"
                        max="32"
                        value={threads}
                        onChange={(e) => setThreads(parseInt(e.target.value))}
                        disabled={isMining || loading}
                        className="w-full accent-accent h-1.5 bg-border/50 rounded-lg appearance-none cursor-pointer"
                    />
                </div>
            </div>

            <div className="mt-auto flex flex-col gap-3 border-t border-border/40 pt-5">
                {isActive ? (
                    <button
                        onClick={() => toggleMining('mining/stop')}
                        disabled={loading}
                        className="glass-btn w-full py-3 bg-status-error/10 border-status-error/30 text-status-error font-medium hover:bg-status-error/20 flex justify-center items-center gap-2 group transition-all"
                    >
                        <AlertTriangle size={16} className="group-hover:animate-pulse" /> {loading ? 'Halting...' : 'Halt Sovereign Consensus'}
                    </button>
                ) : (
                    <div className="flex gap-3">
                        <button
                            onClick={() => toggleMining('mining/start', 'stake')}
                            disabled={loading}
                            className="glass-btn flex-[1] py-3 text-xs font-bold uppercase tracking-widest border-border hover:border-text-secondary transition-colors"
                        >
                            Stake Only
                        </button>
                        <button
                            onClick={() => toggleMining('mining/start', 'mine')}
                            disabled={loading}
                            className="glass-btn flex-[2] py-3 bg-accent/10 border-accent/30 text-accent font-bold uppercase tracking-widest hover:bg-accent/20 shadow-[0_0_20px_rgba(56,189,248,0.1)] flex items-center justify-center gap-2"
                        >
                            {loading ? (
                                <Zap size={16} className="animate-spin text-accent" />
                            ) : (
                                <Zap size={16} className="text-accent-hover" />
                            )}
                            {loading ? 'Starting...' : 'Mine & Stake'}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};
