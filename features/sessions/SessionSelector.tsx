import React, { useEffect } from 'react';
import { useStore } from '../../store/useStore';
import { MessageSquare, Plus } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

/**
 * SessionSelector — Dropdown in chat header showing current session key
 * and recent sessions. Allows rapid switching or creating new sessions.
 */
export const SessionSelector: React.FC = () => {
    const { sessions, setSessions, activeSessionKey, setActiveSessionKey, accessToken } = useStore();

    useEffect(() => {
        const fetchSessions = async () => {
            try {
                const res = await fetch(`${DAEMON_URL}/api/v1/sessions`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include',
                });
                if (res.ok) {
                    const data = await res.json();
                    setSessions(data.sessions || []);
                }
            } catch (err) {
                console.error('[SessionSelector] Failed to fetch sessions:', err);
            }
        };
        fetchSessions();
    }, [accessToken, setSessions]);

    const handleSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const value = e.target.value;
        if (value === 'NEW') {
            setActiveSessionKey(crypto.randomUUID());
        } else {
            setActiveSessionKey(value);
        }
    };

    return (
        <div className="flex items-center gap-2 bg-glass-1 border border-glass-edge rounded-full px-3 py-1.5 backdrop-blur-md">
            <MessageSquare size={14} className="text-text-secondary" />
            <select
                className="bg-transparent border-none text-[11px] glass-label text-text-primary focus:outline-none focus:ring-0 cursor-pointer w-24 md:w-32"
                value={activeSessionKey}
                onChange={handleSelect}
                aria-label="Active Session"
            >
                <option value={activeSessionKey} className="bg-glass-2 text-text-primary">
                    {activeSessionKey.slice(0, 8)}... (Active)
                </option>
                {sessions.filter(s => s.key !== activeSessionKey).map(session => (
                    <option key={session.key} value={session.key} className="bg-glass-2 text-text-primary">
                        {session.key.slice(0, 8)}... ({session.messageCount} msgs)
                    </option>
                ))}
                <option disabled>──────────</option>
                <option value="NEW" className="bg-glass-2 font-bold text-accent">
                    + New Session
                </option>
            </select>
            <button
                onClick={() => setActiveSessionKey(crypto.randomUUID())}
                className="hover:bg-glass-edge rounded-full p-1 transition-colors"
                title="Create New Session"
                aria-label="New session"
            >
                <Plus size={12} className="text-text-secondary hover:text-text-primary" />
            </button>
        </div>
    );
};

export default SessionSelector;
