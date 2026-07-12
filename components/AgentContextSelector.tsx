import React from 'react';
import { useStore } from '../store/useStore';
import { Bot, Crown } from 'lucide-react';

const AgentContextSelector: React.FC = () => {
    const { activeAgentId, setActiveAgentId } = useStore();

    // In a real app, this would be dynamically fetched from the swarm registry.
    // We allow 'executive' and arbitrary IDs here.
    return (
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-[var(--fill-quaternary)] border border-[var(--separator)] hover:bg-[var(--fill-tertiary)] transition-colors">
            <div className={`${activeAgentId === 'executive' ? 'text-amber-400' : 'text-cyan-400'}`}>
                {activeAgentId === 'executive' ? <Crown size={12} /> : <Bot size={12} />}
            </div>
            <input
                type="text"
                value={activeAgentId}
                onChange={(e) => setActiveAgentId(e.target.value.trim() || 'executive')}
                className="w-20 bg-transparent border-none text-[10px] font-mono text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none focus:ring-0 truncate"
                placeholder="agent_id..."
                title="Active Context"
            />
        </div>
    );
};

export default AgentContextSelector;
