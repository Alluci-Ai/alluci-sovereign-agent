import React from 'react';
import { Cpu, DollarSign, Database, ShieldCheck, Activity } from 'lucide-react';

interface WalletOverviewProps {
    data: any;
}

export const WalletOverview: React.FC<WalletOverviewProps> = ({ data }) => {
    if (!data) return null;

    const formatter = new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 8,
    });

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Identity Tile */}
            <div className="glass-panel p-6 relative overflow-hidden group border-white/5 bg-white/[0.02]">
                <div className="absolute inset-0 bg-gradient-to-br from-accent/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
                <div className="flex items-center justify-between mb-6">
                    <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-widest leading-none">Identity Manifest</span>
                    <div className={`p-2 rounded-lg ${data.identity ? 'bg-accent/10 text-accent' : 'bg-white/5 text-text-muted'}`}>
                        <ShieldCheck size={16} />
                    </div>
                </div>
                <div>
                    <h3 className="text-xl font-semibold text-text-primary tracking-tight truncate">
                        {data.identity ? data.identity.name : "Anonymous Node"}
                    </h3>
                    <p className="text-[10px] font-mono text-text-tertiary mt-2 truncate bg-black/20 px-2 py-1 rounded inline-block">
                        {data.identity ? data.identity.identityaddress : "Create VerusID@"}
                    </p>
                </div>
            </div>

            {/* VRSC Balance Tile */}
            <div className="glass-panel p-6 relative overflow-hidden group border-accent/20 bg-accent/[0.03] shadow-[0_8px_32px_rgba(56,189,248,0.05)]">
                <div className="absolute inset-0 bg-gradient-to-br from-accent/20 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
                <div className="flex items-center justify-between mb-6 relative z-10">
                    <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-widest leading-none">Primary Balance</span>
                    <div className="p-2 rounded-lg bg-accent/20 text-accent">
                        <DollarSign size={16} />
                    </div>
                </div>
                <div className="relative z-10">
                    <div className="flex items-baseline gap-2">
                        <h3 className="text-3xl font-bold tracking-tighter text-text-primary">
                            {formatter.format(data.total_vrsc)}
                        </h3>
                        <span className="text-sm font-bold text-accent tracking-widest uppercase">VRSC</span>
                    </div>
                    <div className="mt-4">
                        <span className="text-[9px] font-bold text-text-tertiary items-center flex gap-1.5 bg-black/30 px-2 py-1 rounded border border-white/5 backdrop-blur-md uppercase tracking-tighter">
                            <span className={`w-1.5 h-1.5 rounded-full ${data.unconfirmed > 0 ? 'bg-status-warning animate-pulse' : 'bg-status-success'}`} />
                            {data.unconfirmed > 0 ? `${formatter.format(data.unconfirmed)} Unconfirmed` : 'All funds confirmed'}
                        </span>
                    </div>
                </div>
            </div>

            {/* Bridge Assets */}
            <div className="glass-panel p-6 relative overflow-hidden group border-white/5 bg-white/[0.02]">
                <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
                <div className="flex items-center justify-between mb-6">
                    <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-widest leading-none">Bridge Liquidity</span>
                    <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                        <Database size={16} />
                    </div>
                </div>
                <div className="space-y-3">
                    {data.balances?.filter((b: any) => b.currency !== 'VRSC').slice(0, 3).map((b: any) => (
                        <div key={b.currency} className="flex items-center justify-between group/item">
                            <span className="text-xs font-medium text-text-tertiary group-hover/item:text-text-secondary transition-colors">{b.currency}</span>
                            <span className="font-mono text-xs text-text-primary">{formatter.format(b.amount)}</span>
                        </div>
                    )) || (
                            <div className="text-[10px] text-text-muted italic py-2 text-center border border-dashed border-white/5 rounded">
                                No PBaaS assets found
                            </div>
                        )}
                </div>
            </div>

            {/* Network / PBaaS Status */}
            <div className="glass-panel p-6 relative overflow-hidden group border-white/5 bg-white/[0.02]">
                <div className="absolute inset-0 bg-gradient-to-br from-status-success/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
                <div className="flex items-center justify-between mb-6">
                    <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-widest leading-none">Global Network</span>
                    <div className="p-2 rounded-lg bg-status-success/10 text-status-success">
                        <Activity size={16} />
                    </div>
                </div>
                <div className="space-y-4">
                    <div className="flex items-center justify-between border-b border-white/5 pb-2">
                        <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-tight">Height</span>
                        <span className="text-xs font-mono text-text-primary">{data.blockchain?.blocks.toLocaleString() || '---'}</span>
                    </div>
                    <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold text-text-tertiary uppercase tracking-tight">Consensus</span>
                        <div className="flex items-center gap-2">
                            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded leading-none ${data.blockchain?.synced ? 'text-status-success bg-status-success/10 border border-status-success/20' : 'text-status-warning bg-status-warning/10 border border-status-warning/20'}`}>
                                {data.blockchain?.synced ? 'SYNCED' : 'SYNCING'}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
