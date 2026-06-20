import React, { useEffect, useState } from 'react';
import { useStore } from '../../store/useStore';
import { UserMinus, Users, Clock } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

interface PerAccountListProps {
    channelId: string;
}

export const PerAccountList: React.FC<PerAccountListProps> = ({ channelId }) => {
    const { accessToken } = useStore();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [accounts, setAccounts] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchAccounts = async () => {
            try {
                const res = await fetch(`${DAEMON_URL}/api/v1/channels/${channelId}/accounts`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include'
                });
                if (res.ok) {
                    const data = await res.json();
                    setAccounts(data.accounts || []);
                }
            } catch (err) {
                console.error(`Failed to sync accounts for ${channelId}`, err);
            } finally {
                setLoading(false);
            }
        };
        fetchAccounts();
    }, [channelId, accessToken]);

    const handleDisconnect = async (accountId: string) => {
        if (!confirm('Are you sure you want to permanently sever connection to this account? Context cache will be lost.')) return;

        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/channels/${channelId}/accounts/${accountId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            });
            if (res.ok) {
                setAccounts(prev => prev.filter(a => a.id !== accountId));
            } else {
                alert('Account unlinking failed.');
            }
        } catch (err) {
            console.error('Delete network failure:', err);
        }
    };

    if (loading) return <div className="text-[10px] font-mono opacity-40 animate-pulse">Scanning identity aliases...</div>;

    if (accounts.length === 0) return (
        <div className="bg-glass-2 border border-glass-edge border-dashed rounded-lg p-3 text-center opacity-60">
            <span className="text-[10px] glass-label">NO ACTIVE ALIAS IDENTITIES</span>
        </div>
    );

    return (
        <div className="flex flex-col gap-2 mt-2 border-t border-glass-edge pt-3">
            <h5 className="glass-label text-[10px] opacity-70 flex items-center gap-1 mb-1">
                <Users size={12} /> Bound Account Identities
            </h5>

            {accounts.map(acc => (
                <div key={acc.id} className="flex items-center justify-between p-2 bg-glass-pressed rounded-md border border-white/5 transition-colors hover:border-white/10 group">
                    <div className="flex items-center gap-3">
                        {acc.avatar_url ? (
                            <img src={acc.avatar_url} className="w-6 h-6 rounded-full border border-glass-edge object-cover" />
                        ) : (
                            <div className="w-6 h-6 rounded-full bg-glass-edge flex items-center justify-center text-[10px] opacity-50">
                                ?
                            </div>
                        )}
                        <div className="flex flex-col">
                            <span className="text-[11px] font-medium text-text-primary">{acc.alias}</span>
                            <span className="text-[9px] font-mono text-text-tertiary flex items-center gap-1">
                                <Clock size={8} /> Last seen: {new Date(acc.last_seen || Date.now()).toLocaleDateString()}
                            </span>
                        </div>
                    </div>

                    <button
                        onClick={() => handleDisconnect(acc.id)}
                        className="p-1.5 opacity-0 group-hover:opacity-100 transition-opacity text-status-error hover:bg-status-error/10 rounded-md"
                        title="Sever connection"
                    >
                        <UserMinus size={14} />
                    </button>
                </div>
            ))}
        </div>
    );
};

export default PerAccountList;
