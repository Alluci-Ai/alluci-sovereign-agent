import React, { useState, useEffect } from 'react';
import { usePolytopeAPI } from '../../usePolytopeAPI';

interface Subscription {
    channel_id: string;
    is_active: boolean;
}

export const ChannelSubscriptions: React.FC<{ agentId: string }> = ({ agentId }) => {
    const { getAgentSubscriptions, updateAgentSubscription } = usePolytopeAPI();
    const [subs, setSubs] = useState<Subscription[]>([]);
    const [loading, setLoading] = useState(true);

    const availableChannels = [
        { id: 'telegram', name: 'Telegram Bot API' },
        { id: 'whatsapp', name: 'WhatsApp Business' },
        { id: 'nostr', name: 'Nostr Identity Relay' },
        { id: 'imessage', name: 'iMessage Bridge' },
        { id: 'discord', name: 'Discord Gateway' },
        { id: 'verus', name: 'Verus Wallet ID' },
    ];

    useEffect(() => {
        const load = async () => {
            setLoading(true);
            const data = await getAgentSubscriptions(agentId);
            setSubs(data || []);
            setLoading(false);
        };
        load();
    }, [agentId, getAgentSubscriptions]);

    const toggle = async (channelId: string) => {
        const current = subs.find(s => s.channel_id === channelId);
        const nextState = !current?.is_active;
        
        // Optimistic update
        setSubs(prev => {
            const exists = prev.find(s => s.channel_id === channelId);
            if (exists) {
                return prev.map(s => s.channel_id === channelId ? { ...s, is_active: nextState } : s);
            }
            return [...prev, { channel_id: channelId, is_active: nextState }];
        });

        const res = await updateAgentSubscription(agentId, channelId, nextState);
        if (res.status !== "SUCCESS") {
            // Revert on failure
            setSubs(prev => prev.map(s => s.channel_id === channelId ? { ...s, is_active: !nextState } : s));
        }
    };

    if (loading) return <div className="p-6 text-accent animate-pulse">Syncing Subscriptions...</div>;

    return (
        <div className="bg-glass-1 border border-glass-edge rounded-xl p-6 shadow-sm flex flex-col gap-6 max-w-2xl animate-in zoom-in-95 duration-200">
            <h3 className="glass-label text-[10px] uppercase opacity-70 tracking-widest border-b border-glass-edge pb-2 m-0">Subscription Mapping Conduits</h3>

            <div className="flex flex-col gap-2">
                {availableChannels.map(ch => {
                    const sub = subs.find(s => s.channel_id === ch.id);
                    const isActive = sub?.is_active || false;
                    return (
                        <label
                            key={ch.id}
                            className={`flex items-center gap-4 p-3 rounded-lg border cursor-pointer transition-all ${isActive ? 'bg-glass-pressed border-accent/20 shadow-[0_0_15px_rgba(43,158,255,0.05)]' : 'bg-transparent border-transparent hover:bg-glass-hover'}`}
                        >
                            <input
                                type="checkbox"
                                checked={isActive}
                                onChange={() => toggle(ch.id)}
                                className="bg-black/40 border border-white/20 rounded accent-accent w-4 h-4 cursor-pointer"
                            />
                            <span className={`text-[12px] font-mono tracking-wider ${isActive ? 'text-accent' : 'text-text-secondary'}`}>{ch.name}</span>
                        </label>
                    );
                })}
            </div>

            <p className="text-[10px] text-text-tertiary font-mono opacity-50 flex items-center gap-1 max-w-xs mt-2 text-center md:text-left mx-auto md:mx-0">
                // System strictly rejects unauthorized subscription mapping routes natively
            </p>
        </div>
    );
};

export default ChannelSubscriptions;
