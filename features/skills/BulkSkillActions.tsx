import React, { useState } from 'react';
import { useStore } from '../../store/useStore';
import { LayoutGrid, Trash2, XOctagon } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

interface BulkSkillActionsProps {
    agentId: string;
    onComplete: () => void;
}

export const BulkSkillActions: React.FC<BulkSkillActionsProps> = ({ agentId, onComplete }) => {
    const { accessToken } = useStore();
    const [loading, setLoading] = useState(false);

    const executeBulk = async (action: 'clear' | 'disable-all') => {
        if (!confirm(`Are you sure you want to execute ${action.toUpperCase()} across all bindings on this agent?`)) return;
        setLoading(true);
        try {
            await fetch(`${DAEMON_URL}/api/agents/${agentId}/skills/${action}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            });
            onComplete();
        } catch (err) {
            console.error(`Bulk execution ${action} failed:`, err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex items-center gap-2 border-t border-glass-edge pt-4 mt-2 mb-2 animate-in fade-in duration-500">
            <span className="glass-label text-[10px] tracking-widest text-text-tertiary uppercase flex items-center gap-2 flex-1">
                <LayoutGrid size={12} /> Array Action Overrides
            </span>
            <button
                onClick={() => executeBulk('disable-all')}
                disabled={loading}
                className="glass-btn gap-2 bg-amber-500/10 hover:bg-amber-500/20 text-amber-500 border-amber-500/20"
                style={{ padding: '4px 12px', fontSize: 10 }}
            >
                <XOctagon size={12} /> Disable All Skills
            </button>
            <button
                onClick={() => executeBulk('clear')}
                disabled={loading}
                className="glass-btn gap-2 bg-status-error/10 hover:bg-status-error/20 text-status-error border-status-error/20"
                style={{ padding: '4px 12px', fontSize: 10 }}
            >
                <Trash2 size={12} /> Force Detach All
            </button>
        </div>
    );
};

export default BulkSkillActions;
