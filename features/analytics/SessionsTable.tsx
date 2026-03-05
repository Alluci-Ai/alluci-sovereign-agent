import React, { useState } from 'react';
import { Eye, Clock, Hash, Coins, ArrowUpDown } from 'lucide-react';

interface SessionsTableProps {
    sessions: any[];
    query: string;
}

export const SessionsTable: React.FC<SessionsTableProps> = ({ sessions, query }) => {
    const [sortField, setSortField] = useState<string>('first_turn');
    const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

    const toggleSort = (field: string) => {
        if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        else { setSortField(field); setSortDir('desc'); }
    };

    const filtered = sessions.filter(session => {
        if (!query) return true;
        const search = query.toLowerCase();
        return (
            session.session_key.toLowerCase().includes(search) ||
            session.agent?.toLowerCase().includes(search) ||
            session.provider?.toLowerCase().includes(search) ||
            session.models.some((m: string) => m.toLowerCase().includes(search))
        );
    });

    const sorted = [...filtered].sort((a, b) => {
        let va = a[sortField] ?? 0;
        let vb = b[sortField] ?? 0;
        if (sortField === 'tokens') {
            va = a.total_input + a.total_output;
            vb = b.total_input + b.total_output;
        } else if (sortField === 'cost') {
            va = a.total_cost;
            vb = b.total_cost;
        } else if (sortField === 'model') {
            va = a.models[0] || '';
            vb = b.models[0] || '';
        }

        const cmp = typeof va === 'string' ? va.localeCompare(vb as string) : (va as number) - (vb as number);
        return sortDir === 'asc' ? cmp : -cmp;
    });

    const formatTokens = (num: number) => {
        if (num > 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    };

    return (
        <div className="overflow-x-auto w-full">
            <table className="w-full text-left text-sm text-text-primary">
                <thead className="text-xs text-text-secondary uppercase border-b border-glass-edge">
                    <tr>
                        <th className="py-3 px-4 font-semibold tracking-wider cursor-pointer hover:text-text-primary transition-colors" onClick={() => toggleSort('session_key')}>
                            Session {sortField === 'session_key' && <ArrowUpDown size={10} className="inline ml-1" />}
                        </th>
                        <th className="py-3 px-4 font-semibold tracking-wider cursor-pointer hover:text-text-primary transition-colors" onClick={() => toggleSort('agent')}>
                            Agent {sortField === 'agent' && <ArrowUpDown size={10} className="inline ml-1" />}
                        </th>
                        <th className="py-3 px-4 font-semibold tracking-wider cursor-pointer hover:text-text-primary transition-colors" onClick={() => toggleSort('provider')}>
                            Provider {sortField === 'provider' && <ArrowUpDown size={10} className="inline ml-1" />}
                        </th>
                        <th className="py-3 px-4 font-semibold tracking-wider cursor-pointer hover:text-text-primary transition-colors" onClick={() => toggleSort('model')}>
                            Model {sortField === 'model' && <ArrowUpDown size={10} className="inline ml-1" />}
                        </th>
                        <th className="py-3 px-4 font-semibold tracking-wider cursor-pointer hover:text-text-primary transition-colors" onClick={() => toggleSort('messages')}>
                            Messages {sortField === 'messages' && <ArrowUpDown size={10} className="inline ml-1" />}
                        </th>
                        <th className="py-3 px-4 font-semibold tracking-wider cursor-pointer hover:text-text-primary transition-colors text-right" onClick={() => toggleSort('tokens')}>
                            Tokens {sortField === 'tokens' && <ArrowUpDown size={10} className="inline ml-1" />}
                        </th>
                        <th className="py-3 px-4 font-semibold tracking-wider cursor-pointer hover:text-text-primary transition-colors text-right" onClick={() => toggleSort('cost')}>
                            Cost {sortField === 'cost' && <ArrowUpDown size={10} className="inline ml-1" />}
                        </th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-glass-edge/50">
                    {sorted.length === 0 ? (
                        <tr>
                            <td colSpan={7} className="text-center py-8 text-text-secondary text-sm">
                                No sessions match your filter.
                            </td>
                        </tr>
                    ) : sorted.map((session, i) => {
                        const tokens = session.total_input + session.total_output;
                        return (
                            <tr key={`${session.session_key}-${i}`} className="hover:bg-glass-2 transition-colors cursor-pointer group">
                                <td className="py-3 px-4">
                                    <span className="font-mono text-[11px] bg-emerald-900/20 text-emerald-400 border border-emerald-500/20 px-2 py-1 rounded inline-block">
                                        {session.session_key}
                                    </span>
                                </td>
                                <td className="py-3 px-4">
                                    <span className="text-[10px] font-bold tracking-wider bg-white/5 text-white/70 border border-white/10 px-2.5 py-1 rounded-full uppercase">
                                        {session.agent || 'SYSTEM'}
                                    </span>
                                </td>
                                <td className="py-3 px-4 text-text-secondary font-mono text-[11px]">
                                    {session.provider || 'anthropic'}
                                </td>
                                <td className="py-3 px-4 text-text-secondary font-mono text-[11px]">
                                    {session.models.length > 0 ? session.models[0] : 'unknown'}
                                </td>
                                <td className="py-3 px-4 text-text-secondary text-xs">
                                    {session.messages || session.turn_count * 2}
                                </td>
                                <td className="py-3 px-4 text-right font-mono text-[11px] text-text-secondary">
                                    {formatTokens(tokens)}
                                </td>
                                <td className="py-3 px-4 text-right font-mono text-[11px] text-amber-500/90 group-hover:text-amber-400 transition-colors">
                                    ${session.total_cost.toFixed(2)}
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    );
};

export default SessionsTable;
