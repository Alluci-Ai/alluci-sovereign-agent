import React, { useState } from 'react';
import { useStore } from '../../store/useStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://127.0.0.1:8000';

interface ChannelToggleProps {
    channelId: string;
    initialEnabled: boolean;
}

export const ChannelToggle: React.FC<ChannelToggleProps> = ({ channelId, initialEnabled }) => {
    const { accessToken } = useStore();
    const [enabled, setEnabled] = useState(initialEnabled);
    const [updating, setUpdating] = useState(false);

    const toggle = async () => {
        setUpdating(true);
        const nextState = !enabled;
        try {
            // Optimistic UI
            setEnabled(nextState);
            const res = await fetch(`${DAEMON_URL}/api/v1/channels/${channelId}/toggle`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ enabled: nextState }),
                credentials: 'include'
            });
            if (!res.ok) {
                setEnabled(!nextState); // Rollback
                console.error('Failed to toggle bridge');
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
                className={`relative w-8 h-4 rounded-full transition-colors duration-300 ease-in-out cursor-pointer ${enabled ? 'bg-status-good' : 'bg-glass-edge'}`}
            >
                <div
                    className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full shadow-sm transition-transform duration-300 ease-in-out ${enabled ? 'transform translate-x-4' : ''}`}
                />
            </button>
        </div>
    );
};

export default ChannelToggle;
