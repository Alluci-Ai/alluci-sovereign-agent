import React, { useState, useEffect, useRef } from 'react';
import { useStore } from '../store/useStore';
import { Bot, Crown, ChevronDown } from 'lucide-react';
import { sovereignService } from '../sovereignService';

const AgentContextSelector: React.FC = () => {
    const { activeAgentId, setActiveAgentId } = useStore();
    const [agents, setAgents] = useState<{ id: string; name: string }[]>([]);
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Fetch available agents from the backend
    useEffect(() => {
        let mounted = true;
        sovereignService.listAgents().then((data) => {
            if (mounted && Array.isArray(data)) {
                setAgents(data.map((a: any) => ({ id: a.id, name: a.name || a.id })));
            }
        }).catch(e => console.error("Failed to fetch agents for context selector", e));
        return () => { mounted = false; };
    }, []);

    // Handle click outside to close dropdown
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const selectedAgentName = activeAgentId === 'executive' 
        ? 'Executive' 
        : (agents.find(a => a.id === activeAgentId)?.name || activeAgentId);

    return (
        <div className="relative" ref={dropdownRef}>
            <div 
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-[var(--fill-quaternary)] border border-[var(--separator)] hover:bg-[var(--fill-tertiary)] transition-colors cursor-pointer select-none"
                title="Active Context"
            >
                <div className={`${activeAgentId === 'executive' ? 'text-amber-400' : 'text-cyan-400'}`}>
                    {activeAgentId === 'executive' ? <Crown size={12} /> : <Bot size={12} />}
                </div>
                <div className="w-20 bg-transparent border-none text-[10px] font-mono text-[var(--text-primary)] truncate flex items-center">
                    <span className="truncate flex-1">{selectedAgentName}</span>
                </div>
                <ChevronDown size={12} className={`text-[var(--text-tertiary)] transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </div>

            {isOpen && (
                <ul className="absolute top-full mt-1 left-0 z-50 w-48 py-1 rounded-md bg-[var(--fill-secondary)] border border-[var(--separator)] shadow-xl backdrop-blur-xl overflow-hidden animate-in fade-in slide-in-from-top-1 duration-100">
                    <li 
                        onClick={() => { setActiveAgentId('executive'); setIsOpen(false); }}
                        className="flex items-center gap-2 px-3 py-1.5 text-xs text-[var(--text-primary)] hover:bg-[var(--fill-tertiary)] cursor-pointer transition-colors"
                    >
                        <Crown size={14} className="text-amber-400 shrink-0" />
                        <span className="font-mono truncate">Executive</span>
                    </li>
                    
                    {agents.filter(a => a.id !== 'executive').map(agent => (
                        <li 
                            key={agent.id}
                            onClick={() => { setActiveAgentId(agent.id); setIsOpen(false); }}
                            className="flex items-center gap-2 px-3 py-1.5 text-xs text-[var(--text-primary)] hover:bg-[var(--fill-tertiary)] cursor-pointer transition-colors"
                        >
                            <Bot size={14} className="text-cyan-400 shrink-0" />
                            <div className="flex flex-col overflow-hidden">
                                <span className="font-mono truncate" title={agent.name}>{agent.name}</span>
                                <span className="text-[9px] text-[var(--text-tertiary)] truncate">{agent.id}</span>
                            </div>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
};

export default AgentContextSelector;
