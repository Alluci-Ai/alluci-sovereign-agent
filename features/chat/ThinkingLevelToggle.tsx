import React, { useEffect, useState } from 'react';
import { useStore } from '../../store/useStore';
import { BrainCircuit } from 'lucide-react';
import { adminService } from '../../adminService';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

/**
 * ThinkingLevelToggle — Top bar header action injecting an explicit thinking boundary
 * per session footprint using the `sessions.patch` mechanism natively out of the RPC logic hook.
 */
export const ThinkingLevelToggle: React.FC = () => {
    const { activeSessionKey, accessToken } = useStore();
    const [thinkingLevel, setThinkingLevel] = useState<string>('MEDIUM');
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        const loadConfig = async () => {
            try {
                const res = await fetch(`${DAEMON_URL}/api/v1/sessions/${activeSessionKey}/config`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include',
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.thinking_level) setThinkingLevel(data.thinking_level);
                }
            } catch (err) {
                console.error('[ThinkingLevelToggle] Failed loading schema config:', err);
            }
        };
        loadConfig();
    }, [activeSessionKey, accessToken]);

    const handleCycle = () => {
        setIsSaving(true);
        const cycleMap: Record<string, string> = {
            'LOW': 'MEDIUM',
            'MEDIUM': 'HIGH',
            'HIGH': 'LOW'
        };

        const nextTarget = cycleMap[thinkingLevel] || 'MEDIUM';
        setThinkingLevel(nextTarget);

        // Instantly patch remote configurations
        adminService.sendRPC('sessions.patch', {
            session_key: activeSessionKey,
            thinking_level: nextTarget
        });

        // Fast flash state visually indicating save cycle
        setTimeout(() => setIsSaving(false), 300);
    };

    return (
        <button
            onClick={handleCycle}
            disabled={isSaving}
            className={`flex items-center gap-2 px-3 py-1.5 border border-glass-edge rounded-full transition-all bg-glass-1 hover:bg-glass-hover ${isSaving ? 'opacity-50' : 'opacity-100'}`}
            title="Cycle Thinking Depth Constraint Target"
        >
            <BrainCircuit size={14} className={thinkingLevel === 'HIGH' ? 'text-accent animate-pulse' : 'text-text-secondary'} />
            <span className="glass-label text-[10px] uppercase text-text-primary min-w-[36px] text-center">
                {thinkingLevel.slice(0, 4)}...
            </span>
        </button>
    );
};

export default ThinkingLevelToggle;
