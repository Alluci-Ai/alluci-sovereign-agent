import React, { useState } from 'react';
import { useStore } from '../../store/useStore';
import { KeyRound, Check } from 'lucide-react';

export const SessionKeyPill: React.FC = () => {
    const { activeSessionKey, setActiveSessionKey } = useStore();
    const [editing, setEditing] = useState(false);
    const [tempKey, setTempKey] = useState('');

    const startEditing = () => {
        setTempKey(activeSessionKey || '');
        setEditing(true);
    };

    const save = () => {
        if (tempKey.trim() && tempKey !== activeSessionKey) {
            setActiveSessionKey(tempKey.trim());
            // In a real app, you'd trigger re-initialization here via store or event
        }
        setEditing(false);
    };

    if (editing) {
        return (
            <div className="flex items-center gap-1 bg-glass-pressed rounded-full border border-accent/30 pl-3 pr-1 h-6 animate-in fade-in slide-in-from-right-2 duration-300">
                <input
                    type="text"
                    value={tempKey}
                    onChange={e => setTempKey(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && save()}
                    onBlur={save}
                    autoFocus
                    className="bg-transparent border-none text-[10px] font-mono tracking-wider w-24 outline-none text-accent"
                />
                <button onClick={save} className="text-accent/70 hover:text-accent p-0.5"><Check size={12} /></button>
            </div>
        );
    }

    return (
        <button
            onClick={startEditing}
            className="flex items-center gap-1.5 bg-glass-1 hover:bg-glass-hover rounded-full border border-glass-edge px-2.5 h-6 transition-colors shadow-sm"
            title="Active Session Key"
        >
            <KeyRound size={10} className="text-text-tertiary" />
            <span className="text-[10px] font-mono tracking-wider text-text-secondary">
                {activeSessionKey ? activeSessionKey.slice(0, 8) : 'NEW_SESS'}
            </span>
        </button>
    );
};

export default SessionKeyPill;
