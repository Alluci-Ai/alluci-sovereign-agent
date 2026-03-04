import React, { useState } from 'react';

// Channel mock up until `agent_channel_subscriptions` table logic exists completely out of the UI
export const ChannelSubscriptions: React.FC<{ agentId: string }> = ({ agentId }) => {
    const [subs, setSubs] = useState([
        { id: 'telegram', name: 'Telegram Bot API', active: true },
        { id: 'whatsapp', name: 'WhatsApp Business', active: false },
        { id: 'nostr', name: 'Nostr Identity Relay', active: true },
        { id: 'imessage', name: 'iMessage Bridge', active: false },
    ]);

    const toggle = (id: string) => {
        setSubs(prev => prev.map(s => s.id === id ? { ...s, active: !s.active } : s));
        // Mocking background persistence immediately natively out of array loops
    };

    return (
        <div className="bg-glass-1 border border-glass-edge rounded-xl p-6 shadow-sm flex flex-col gap-6 max-w-2xl animate-in zoom-in-95 duration-200">
            <h3 className="glass-label text-[10px] uppercase opacity-70 tracking-widest border-b border-glass-edge pb-2 m-0">Subscription Mapping Conduits</h3>

            <div className="flex flex-col gap-2">
                {subs.map(s => (
                    <label
                        key={s.id}
                        className={`flex items-center gap-4 p-3 rounded-lg border cursor-pointer transition-all ${s.active ? 'bg-glass-pressed border-accent/20 shadow-[0_0_15px_rgba(43,158,255,0.05)]' : 'bg-transparent border-transparent hover:bg-glass-hover'}`}
                    >
                        <input
                            type="checkbox"
                            checked={s.active}
                            onChange={() => toggle(s.id)}
                            className="bg-black/40 border border-white/20 rounded accent-accent w-4 h-4 cursor-pointer"
                        />
                        <span className={`text-[12px] font-mono tracking-wider ${s.active ? 'text-accent' : 'text-text-secondary'}`}>{s.name}</span>
                    </label>
                ))}
            </div>

            <p className="text-[10px] text-text-tertiary font-mono opacity-50 flex items-center gap-1 max-w-xs mt-2 text-center md:text-left mx-auto md:mx-0">
                // System strictly rejects unauthorized subscription mapping routes natively
            </p>
        </div>
    );
};

export default ChannelSubscriptions;
