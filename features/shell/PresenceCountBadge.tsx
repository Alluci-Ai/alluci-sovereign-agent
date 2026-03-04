import React from 'react';
import { useStore } from '../../store/useStore';
import { Activity, Server } from 'lucide-react';

export const PresenceCountBadge: React.FC = () => {
    const { presence } = useStore();

    return (
        <div className="flex items-center gap-2 bg-glass-1 rounded-full border border-glass-edge px-2.5 h-6">
            <div className="flex items-center gap-1.5" title="Connected Client Instances">
                <Server size={10} className="text-status-good" />
                <span className="text-[10px] font-mono font-medium text-text-primary">{presence?.instances || 1}</span>
            </div>

            <div className="w-px h-3 bg-glass-edge" />

            <div className="flex items-center gap-1.5" title="Active Sessions">
                <Activity size={10} className="text-accent" />
                <span className="text-[10px] font-mono font-medium text-text-primary">{presence?.sessions || 1}</span>
            </div>
        </div>
    );
};

export default PresenceCountBadge;
