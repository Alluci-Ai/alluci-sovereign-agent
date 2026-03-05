import React from 'react';
import { ArrowUpRight, ArrowDownLeft, RefreshCcw, Coins, CodeXml } from 'lucide-react';

interface WalletTransactionsProps {
    recent?: any[];
}

export const WalletTransactions: React.FC<WalletTransactionsProps> = ({ recent }) => {
    if (!recent || recent.length === 0) {
        return (
            <div className="glass-panel p-8 flex flex-col items-center justify-center text-text-tertiary">
                <CodeXml size={32} className="mb-4 text-border" />
                <p>No recent transactions found on this node.</p>
            </div>
        );
    }

    const getIcon = (category: string) => {
        switch (category) {
            case 'send': return <ArrowUpRight size={16} className="text-status-error" />;
            case 'receive': return <ArrowDownLeft size={16} className="text-status-success" />;
            case 'generate':
            case 'immature': return <Coins size={16} className="text-[#EAB308]" />;
            case 'convert': return <RefreshCcw size={16} className="text-[#A855F7]" />;
            default: return <CodeXml size={16} className="text-text-muted" />;
        }
    };

    const getStatusStyle = (category: string, confirmations: number) => {
        if (confirmations === 0) return "text-status-warning bg-status-warning/10 border-status-warning/20 border";
        if (category === 'immature') return "text-[#EAB308] bg-[#EAB308]/10 border-[#EAB308]/20 border";
        return "text-status-success bg-status-success/10 border-status-success/20 border";
    };

    return (
        <div className="glass-panel overflow-hidden">
            <div className="px-6 py-4 border-b border-border/40 flex items-center justify-between">
                <h3 className="font-medium text-text-primary">Recent Activity</h3>
                <span className="text-xs font-mono text-text-tertiary bg-surface-base/50 px-2 py-1 rounded">Latest 10</span>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="bg-surface-base/30 text-xs uppercase tracking-wider text-text-tertiary border-b border-border/40">
                            <th className="px-6 py-3 font-medium">Type</th>
                            <th className="px-6 py-3 font-medium">Date</th>
                            <th className="px-6 py-3 font-medium">Amount</th>
                            <th className="px-6 py-3 font-medium">Address</th>
                            <th className="px-6 py-3 font-medium">Status</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border/20">
                        {recent.map((tx, idx) => (
                            <tr key={idx} className="hover:bg-surface-elevated/30 transition-colors group">
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <div className="flex items-center gap-3">
                                        <div className={`p-2 rounded-full bg-surface-base/80 shadow-[0_2px_8px_rgba(0,0,0,0.2)] border border-border/40 flex items-center justify-center`}>
                                            {getIcon(tx.category)}
                                        </div>
                                        <span className="text-sm font-medium text-text-secondary capitalize">{tx.category}</span>
                                    </div>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <div className="text-xs text-text-secondary">{tx.time ? new Date(tx.time).toLocaleDateString() : 'Pending'}</div>
                                    <div className="text-[10px] text-text-tertiary">{tx.time ? new Date(tx.time).toLocaleTimeString() : '---'}</div>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <div className={`text-sm font-mono font-medium tracking-tight ${tx.amount > 0 ? 'text-status-success' : 'text-text-primary'}`}>
                                        {tx.amount > 0 ? '+' : ''}{tx.amount.toFixed(4)} <span className="text-xs text-text-tertiary">{tx.currency}</span>
                                    </div>
                                    {tx.fee < 0 && (
                                        <div className="text-[10px] font-mono text-text-muted mt-0.5">fee: {Math.abs(tx.fee).toFixed(5)}</div>
                                    )}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <div className="text-xs font-mono text-text-tertiary w-32 truncate group-hover:text-accent transition-colors cursor-pointer" title={tx.address}>
                                        {tx.address || 'Network'}
                                    </div>
                                    {tx.comment && (
                                        <div className="text-[10px] text-text-muted mt-1 w-32 truncate" title={tx.comment}>{tx.comment}</div>
                                    )}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                    <div className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${getStatusStyle(tx.category, tx.confirmations)}`}>
                                        {tx.confirmations === 0 ? 'Mempool' : tx.category === 'immature' ? `${tx.confirmations} Confs` : 'Confirmed'}
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            <div className="p-4 border-t border-border/40 text-center">
                <button className="text-sm font-medium text-accent hover:text-accent-hover transition-colors inline-flex items-center gap-1">
                    View Full History <ArrowUpRight size={14} />
                </button>
            </div>
        </div>
    );
};
