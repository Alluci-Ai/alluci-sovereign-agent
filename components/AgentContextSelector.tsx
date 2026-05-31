import React from 'react';
import { useStore } from '../store/useStore';
import { Bot, Crown } from 'lucide-react';

const AgentContextSelector: React.FC = () => {
    const { activeAgentId, setActiveAgentId } = useStore();

    // In a real app, this would be dynamically fetched from the swarm registry.
    // We allow 'executive' and arbitrary IDs here.
    return (
        <div className="flex items-center gap-2 p-2 mx-3 mb-2 bg-black/30 border border-white/10 rounded-xl">
            <div className={`p-1.5 rounded-lg ${activeAgentId === 'executive' ? 'bg-amber-500/20 text-amber-400' : 'bg-cyan-500/20 text-cyan-400'}`}>
                {activeAgentId === 'executive' ? <Crown size={14} /> : <Bot size={14} />}
            </div>
            <div className="flex-1 min-w-0">
                <p className="text-[10px] text-gray-500 uppercase tracking-widest font-bold">Active Context</p>
                <input
                    type="text"
                    value={activeAgentId}
                    onChange={(e) => setActiveAgentId(e.target.value.trim() || 'executive')}
                    className="w-full bg-transparent border-none text-xs font-mono text-white placeholder-gray-600 focus:outline-none focus:ring-0 truncate"
                    placeholder="agent_id..."
                />
            </div>
        </div>
    );
};

export default AgentContextSelector;
