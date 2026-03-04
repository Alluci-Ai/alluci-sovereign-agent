import React, { useState } from 'react';
import { Eye, Clock, Hash, Coins, ArrowUpDown } from 'lucide-react';

interface SessionsTableProps {
    sessions: any[];
    loading: boolean;
    onRowClick: (key: string) => void;
}

export const SessionsTable: React.FC<SessionsTableProps> = ({ sessions, loading, onRowClick }) => {
    const [sortField, setSortField] = useState<'first_turn' | 'total_input' | 'total_cost'>('first_turn');
    const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

    // Column Visibility State
    const [cols, setCols] = useState({
        key: true,
        start: true,
        models: true,
        tokensIn: true,
        tokensOut: true,
        cost: true,
        turns: true
    });

    const [showColMenu, setShowColMenu] = useState(false);

    const toggleSort = (field: typeof sortField) => {
        if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        else { setSortField(field); setSortDir('desc'); }
    };

    const sorted = [...sessions].sort((a, b) => {
        const va = a[sortField] ?? 0;
        const vb = b[sortField] ?? 0;
        const cmp = typeof va === 'string' ? va.localeCompare(vb as string) : (va as number) - (vb as number);
        return sortDir === 'asc' ? cmp : -cmp;
    });

    return (
        <div className="bg-glass-1 border border-glass-edge rounded-xl p-5 flex flex-col gap-4 relative">
            <div className="flex items-center justify-between">
                <h3 className="glass-label text-sm tracking-wider">Session Ledgers</h3>

                <div className="relative">
                    <button
                        onClick={() => setShowColMenu(!showColMenu)}
                        className="glass-btn flex items-center gap-2 text-xs px-3 py-1.5"
                    >
                        <Eye size={14} /> View
                    </button>

                    {showColMenu && (
                        <div className="absolute right-0 top-full mt-2 bg-glass-2 border border-glass-edge rounded-lg p-3 shadow-xl backdrop-blur-xl z-50 flex flex-col gap-2 min-w-[160px]">
                            <span className="text-[10px] glass-label text-text-tertiary mb-1">CONFIGURE COLUMNS</span>
                            {Object.entries(cols).map(([col, isVisible]) => (
                                <label key={col} className="flex items-center gap-2 text-xs text-text-primary hover:text-accent cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={isVisible}
                                        onChange={() => setCols(prev => ({ ...prev, [col]: !isVisible }))}
                                        className="accent-accent"
                                    />
                                    {col.toUpperCase()}
                                </label>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="overflow-x-auto">
                <table className="sessions-table w-full">
                    <thead>
                        <tr>
                            {cols.key && <th>Session Key</th>}
                            {cols.start && (
                                <th className="sortable" onClick={() => toggleSort('first_turn')}>
                                    <Clock size={12} /> Start {sortField === 'first_turn' && <ArrowUpDown size={10} />}
                                </th>
                            )}
                            {cols.models && <th>Models Touched</th>}
                            {cols.turns && <th><Hash size={12} /> Turns</th>}
                            {cols.tokensIn && (
                                <th className="sortable text-right" onClick={() => toggleSort('total_input')}>
                                    Tokens In {sortField === 'total_input' && <ArrowUpDown size={10} />}
                                </th>
                            )}
                            {cols.tokensOut && <th className="text-right">Tokens Out</th>}
                            {cols.cost && (
                                <th className="sortable text-right" onClick={() => toggleSort('total_cost')}>
                                    <Coins size={12} /> Cost {sortField === 'total_cost' && <ArrowUpDown size={10} />}
                                </th>
                            )}
                        </tr>
                    </thead>
                    <tbody>
                        {loading && sessions.length === 0 ? (
                            <tr><td colSpan={7} className="text-center py-8 opacity-50">Loading sessions...</td></tr>
                        ) : sorted.length === 0 ? (
                            <tr><td colSpan={7} className="text-center py-8 opacity-50">No sessions match filters</td></tr>
                        ) : sorted.map(session => (
                            <tr
                                key={session.session_key}
                                onClick={() => onRowClick(session.session_key)}
                                className="cursor-pointer hover:bg-glass-hover transition-colors"
                            >
                                {cols.key && <td className="font-mono text-[11px]">{session.session_key.slice(0, 12)}…</td>}
                                {cols.start && <td className="text-[11px]">{new Date(session.first_turn).toLocaleString()}</td>}
                                {cols.models && <td className="text-[11px] opacity-70">{session.models.join(', ')}</td>}
                                {cols.turns && <td className="text-[11px] text-center">{session.turn_count}</td>}
                                {cols.tokensIn && <td className="text-[11px] text-right font-mono">{session.total_input.toLocaleString()}</td>}
                                {cols.tokensOut && <td className="text-[11px] text-right font-mono">{session.total_output.toLocaleString()}</td>}
                                {cols.cost && <td className="text-[11px] text-right font-mono text-status-good">${session.total_cost.toFixed(4)}</td>}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default SessionsTable;
