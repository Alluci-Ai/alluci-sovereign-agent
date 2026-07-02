import React, { useState, useEffect } from 'react';
import { usePolytopeAPI } from '../../usePolytopeAPI';

interface Subscription {
    channel_id: string;
    is_active: boolean;
}

export const ChannelSubscriptions: React.FC<{ agentId: string }> = ({ agentId }) => {
    const { getAgentSubscriptions, getChannelsStatus, updateAgentSubscription } = usePolytopeAPI();
    const [subs, setSubs] = useState<Subscription[]>([]);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [availableChannels, setAvailableChannels] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    const channelNames: Record<string, string> = {
        'telegram': 'Telegram Bot API',
        'whatsapp': 'WhatsApp Business',
        'nostr': 'Nostr Identity Relay',
        'imessage': 'iMessage Bridge',
        'discord': 'Discord Gateway',
        'verus': 'Verus Wallet ID',
        'webchat': 'WebChat Gateway'
    };

    useEffect(() => {
        const load = async () => {
            setLoading(true);
            const [subsData, channelsData] = await Promise.all([
                getAgentSubscriptions(agentId),
                getChannelsStatus()
            ]);
            setSubs(subsData || []);
            setAvailableChannels(channelsData.channels || []);
            setLoading(false);
        };
        load();
    }, [agentId, getAgentSubscriptions, getChannelsStatus]);

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
                    const sub = subs.find(s => s.channel_id === ch.channel);
                    const isActive = sub?.is_active || false;
                    const displayName = channelNames[ch.channel] || ch.channel.charAt(0).toUpperCase() + ch.channel.slice(1);
                    return (
                        <div
                            key={ch.channel}
                            onClick={() => toggle(ch.channel)}
                            className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-all ${isActive ? 'bg-glass-pressed border-accent/20 shadow-[0_0_15px_rgba(43,158,255,0.05)]' : 'bg-transparent border-transparent hover:bg-glass-hover'}`}
                        >
                            <div className="flex items-center gap-4">
                                <input
                                    type="checkbox"
                                    checked={isActive}
                                    readOnly
                                    className="bg-black/40 border border-white/20 rounded accent-accent w-4 h-4 cursor-pointer pointer-events-none"
                                />
                                <span className={`text-[12px] font-mono tracking-wider ${isActive ? 'text-accent' : 'text-text-secondary'}`}>{displayName}</span>
                            </div>
                            <div className="flex items-center gap-1.5 opacity-60">
                                <div className={`w-1.5 h-1.5 rounded-full ${ch.connected ? 'bg-status-good' : 'bg-status-error'}`} />
                                <span className="text-[9px] font-mono uppercase">{ch.connected ? 'Connected' : 'Offline'}</span>
                            </div>
                        </div>
                    );
                })}
            </div>

            <p className="text-[10px] text-text-tertiary font-mono opacity-50 flex items-center gap-1 max-w-xs mt-2 text-center md:text-left mx-auto md:mx-0">
                Click a conduit to authorize or revoke subscription mapping for this agent.
            </p>
        </div>
    );
};

export default ChannelSubscriptions;
