import React, { useState } from 'react';
import { useStore } from '../../store/useStore';
import { Trash2 } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

interface DeleteSessionButtonProps {
    sessionKey: string;
}

/**
 * DeleteSessionButton — Dedicated wipe/purge control for a specific session wrapper explicitly.
 * Includes a native window.confirm verification prompt prior to executing the mutation and 
 * synchronously updates the local Zustand sessions array store.
 */
export const DeleteSessionButton: React.FC<DeleteSessionButtonProps> = ({ sessionKey }) => {
    const { sessions, setSessions, activeSessionKey, setActiveSessionKey, accessToken } = useStore();
    const [isDeleting, setIsDeleting] = useState(false);

    const handleDelete = async (e: React.MouseEvent) => {
        e.stopPropagation();

        if (!window.confirm(`Are you sure you want to permanently delete session ${sessionKey.slice(0, 8)}...? This cannot be undone.`)) {
            return;
        }

        setIsDeleting(true);
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/sessions/${sessionKey}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include',
            });

            if (res.ok) {
                const updatedSessions = sessions.filter(s => (s.session_key || s.key) !== sessionKey);
                setSessions(updatedSessions);

                // If we deleted the active one, fallback safely
                if (activeSessionKey === sessionKey) {
                    if (updatedSessions.length > 0) {
                        const next = updatedSessions[0];
                        setActiveSessionKey(next.session_key || next.key);
                    } else {
                        setActiveSessionKey(crypto.randomUUID());
                    }
                }
            }
        } catch (err) {
            console.error('[DeleteSessionButton] Failure purging session:', err);
        } finally {
            setIsDeleting(false);
        }
    };

    return (
        <button
            onClick={handleDelete}
            disabled={isDeleting}
            className={`sessions-table__delete p-1.5 rounded-full hover:bg-tension/10 hover:text-tension transition-colors ${isDeleting ? 'opacity-50 animate-pulse' : ''}`}
            title="Purge session"
        >
            <Trash2 size={13} />
        </button>
    );
};

export default DeleteSessionButton;
