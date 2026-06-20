import React, { useState, useEffect } from 'react';
import { useStore } from '../../store/useStore';
import { getCsrfToken } from '../../csrfStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

interface ChannelToggleProps {
    channelId: string;
    initialEnabled: boolean;
}

export const ChannelToggle: React.FC<ChannelToggleProps> = ({ channelId, initialEnabled }) => {
    const { accessToken } = useStore();
    const [enabled, setEnabled] = useState(initialEnabled);
    const [updating, setUpdating] = useState(false);

    // Re-sync local state when the parent config finishes loading and
    // passes a new initialEnabled value (fixes async fetch race).
    useEffect(() => {
        setEnabled(initialEnabled);
    }, [initialEnabled]);

    const toggle = async () => {
        if (updating) return;
        setUpdating(true);
        const nextState = !enabled;
        try {
            // Optimistic UI
            setEnabled(nextState);
            const csrfToken = await getCsrfToken(DAEMON_URL, accessToken);
            const res = await fetch(`${DAEMON_URL}/api/v1/channels/${channelId}/toggle`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json',
                    ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
                },
                body: JSON.stringify({ enabled: nextState }),
                credentials: 'include'
            });
            if (!res.ok) {
                setEnabled(!nextState); // Rollback
                console.error(`Failed to toggle bridge ${channelId}: ${res.status}`);
            }
        } catch (err) {
            setEnabled(!nextState);
            console.error('Network error during bridge toggle', err);
        } finally {
            setUpdating(false);
        }
    };

    return (
        <div className="flex items-center gap-2">
            <span className="text-[10px] glass-label opacity-70">{enabled ? 'ACTIVE' : 'DORMANT'}</span>
            <button
                onClick={toggle}
                disabled={updating}
                aria-label={`Toggle ${channelId} ${enabled ? 'off' : 'on'}`}
                className="relative w-8 h-4 rounded-full transition-colors duration-300 ease-in-out cursor-pointer"
                style={{ backgroundColor: enabled ? 'var(--status-good, #30d158)' : 'rgba(255,255,255,0.15)' }}
            >
                <div
                    className="absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full shadow-sm transition-transform duration-300 ease-in-out"
                    style={{ transform: enabled ? 'translateX(16px)' : 'translateX(0)' }}
                />
            </button>
        </div>
    );
};

export default ChannelToggle;
