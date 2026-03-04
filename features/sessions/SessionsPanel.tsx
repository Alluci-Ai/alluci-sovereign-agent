import React, { useEffect, useState } from 'react';
import { useStore } from '../../store/useStore';
import { Clock, Hash, Coins, ArrowUpDown, Plus } from 'lucide-react';
import { SessionOverrides } from './SessionOverrides';
import { SessionCostDisplay } from './SessionCostDisplay';
import { DeleteSessionButton } from './DeleteSessionButton';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

/**
 * SessionsPanel — Dedicated sessions management view.
 * Lists all sessions with token counts, costs, and controls.
 */
export const SessionsPanel: React.FC = () => {
    const { sessions, setSessions, activeSessionKey, setActiveSessionKey, accessToken } = useStore();
    const [sortField, setSortField] = useState<'created' | 'tokens' | 'cost'>('created');
    const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
    const [loading, setLoading] = useState(false);

    const fetchSessions = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${DAEMON_URL}/api/sessions`, {
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include',
            });
            if (res.ok) {
                const data = await res.json();
                setSessions(data.sessions || []);
            }
        } catch (err) {
            console.error('[SessionsPanel] Failed to fetch sessions:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchSessions(); }, []);

    // (Removed duplicate inline handleDelete function, logic shifted to DeleteSessionButton)

    const handleNewSession = () => {
        const newKey = crypto.randomUUID();
        setActiveSessionKey(newKey);
    };

    const sorted = [...sessions].sort((a, b) => {
        const va = a[sortField] ?? 0;
        const vb = b[sortField] ?? 0;
        const cmp = typeof va === 'string' ? va.localeCompare(vb as string) : (va as number) - (vb as number);
        return sortDir === 'asc' ? cmp : -cmp;
    });

    const toggleSort = (field: typeof sortField) => {
        if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
        else { setSortField(field); setSortDir('desc'); }
    };

    return (
        <div className="inline-panel-wrapper">
            <div className="inline-panel">
                <div className="inline-panel__header">
                    <h2 className="inline-panel__title">Sessions</h2>
                    <button onClick={handleNewSession} className="glass-btn" style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
                        <Plus size={14} /> New Session
                    </button>
                </div>

                <div className="inline-panel__body flex flex-col xl:flex-row gap-6" style={{ overflow: 'auto' }}>
                    <div className="flex-1">
                        {loading ? (
                            <div className="inline-panel__empty"><p>Loading sessions…</p></div>
                        ) : sessions.length === 0 ? (
                            <div className="inline-panel__empty">
                                <p>No sessions yet.</p>
                                <p className="text-xs opacity-50">Start a conversation to create your first session.</p>
                            </div>
                        ) : (
                            <table className="sessions-table">
                                <thead>
                                    <tr>
                                        <th>Session Key</th>
                                        <th>Model</th>
                                        <th className="sortable" onClick={() => toggleSort('created')}>
                                            <Clock size={12} /> Created {sortField === 'created' && <ArrowUpDown size={10} />}
                                        </th>
                                        <th><Hash size={12} /> Messages</th>
                                        <th className="sortable" onClick={() => toggleSort('tokens')}>
                                            Tokens {sortField === 'tokens' && <ArrowUpDown size={10} />}
                                        </th>
                                        <th className="sortable" onClick={() => toggleSort('cost')}>
                                            <Coins size={12} /> Cost {sortField === 'cost' && <ArrowUpDown size={10} />}
                                        </th>
                                        <th></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {sorted.map(session => (
                                        <tr
                                            key={session.key}
                                            className={activeSessionKey === session.key ? 'sessions-table__row--active' : ''}
                                            onClick={() => setActiveSessionKey(session.key)}
                                        >
                                            <td className="font-mono text-[11px]">{session.key.slice(0, 12)}…</td>
                                            <td className="text-[11px]">{session.model || '—'}</td>
                                            <td className="text-[11px]">{new Date(session.created).toLocaleDateString()}</td>
                                            <td className="text-[11px] text-center">{session.messageCount}</td>
                                            <td className="text-[11px] text-center">{session.tokens?.toLocaleString() ?? '—'}</td>
                                            <td className="text-[11px] text-center">${(session.cost ?? 0).toFixed(4)}</td>
                                            <td>
                                                <DeleteSessionButton sessionKey={session.key} />
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>

                    {/* Sprint B - Sidebar Analytics/Overrides bounded to activeSessionKey */}
                    <div className="w-full xl:w-80 flex flex-col gap-4 flex-none">
                        <SessionCostDisplay />
                        <SessionOverrides />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SessionsPanel;
