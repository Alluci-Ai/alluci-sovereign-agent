import React, { useState } from 'react';
import { getCsrfToken } from '../csrfStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

// Inline StringArrayEditor for the Tool Editor
const EditorList: React.FC<{
    label: string;
    items: string[];
    onChange: (newItems: string[]) => void;
    placeholder: string;
}> = ({ label, items, onChange, placeholder }) => {
    const [val, setVal] = useState('');
    const add = () => {
        if (!val.trim()) return;
        onChange([...items, val.trim()]);
        setVal('');
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>
            <label style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.02em' }}>{label}</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {items.map((it, i) => (
                    <span key={i} style={{
                        display: 'inline-flex', alignItems: 'center', gap: 4,
                        padding: '4px 8px',
                        background: 'var(--fill-quaternary)',
                        border: '1px solid var(--separator)',
                        borderRadius: 6,
                        fontSize: 12, fontFamily: 'var(--font-mono)',
                        color: 'var(--text-primary)',
                    }}>
                        {it}
                        <button onClick={() => onChange(items.filter((_, idx) => idx !== i))}
                            style={{ background: 'none', border: 'none', color: 'var(--accent-danger)', cursor: 'pointer', fontSize: 14, lineHeight: 1, padding: 0 }}>×</button>
                    </span>
                ))}
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
                <input
                    className="glass-input"
                    value={val}
                    onChange={e => setVal(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && add()}
                    placeholder={placeholder}
                    style={{ flex: 1, padding: '6px 10px', fontSize: 13 }}
                />
                <button onClick={add} className="glass-btn" style={{ padding: '6px 12px', flexShrink: 0 }}>+</button>
            </div>
        </div>
    );
};

interface ModularToolEditorProps {
    tool: any;
    onClose: () => void;
    onSaveGlobal: (updatedTool: any) => Promise<void>;
    onForkAndAssign: (forkedTool: any) => Promise<void>;
}

export const ModularToolEditor: React.FC<ModularToolEditorProps> = ({ tool, onClose, onSaveGlobal, onForkAndAssign }) => {
    const [localTool, setLocalTool] = useState({ ...tool });
    const [saving, setSaving] = useState(false);
    const [forking, setForking] = useState(false);

    const handleSaveGlobal = async () => {
        setSaving(true);
        try {
            const token = localStorage.getItem('alluci_daemon_token');
            const csrfToken = await getCsrfToken(DAEMON_URL, token);
            const res = await fetch(`${DAEMON_URL}/api/v1/tools/${localTool.id}`, {
                method: 'PUT',
                headers: { 
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
                    ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {})
                },
                body: JSON.stringify(localTool)
            });
            if (!res.ok) throw new Error("Failed to save global tool");
            await onSaveGlobal(localTool);
        } catch (e) {
            console.error("Save global failed", e);
            alert("Failed to save global tool.");
        } finally {
            setSaving(false);
        }
    };

    const handleFork = async () => {
        setForking(true);
        try {
            const newId = `${localTool.id}_fork_${Date.now()}`;
            const forked = {
                ...localTool,
                id: newId,
                name: `${localTool.name} (Fork)`,
            };
            
            const token = localStorage.getItem('alluci_daemon_token');
            const csrfToken = await getCsrfToken(DAEMON_URL, token);
            const res = await fetch(`${DAEMON_URL}/api/v1/tools/${newId}`, {
                method: 'PUT',
                headers: { 
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
                    ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {})
                },
                body: JSON.stringify(forked)
            });
            if (!res.ok) throw new Error("Failed to fork tool");
            await onForkAndAssign(forked);
        } catch (e) {
            console.error("Fork failed", e);
            alert("Failed to fork tool.");
        } finally {
            setForking(false);
        }
    };

    const updateArray = (key: string, arr: string[]) => {
        setLocalTool({ ...localTool, [key]: arr });
    };

    return (
        <div style={{
            position: 'fixed', top: 0, right: 0, bottom: 0, width: 450,
            background: 'var(--bg-glass-2)',
            backdropFilter: 'blur(30px) saturate(120%)',
            borderLeft: '1px solid var(--glass-edge)',
            zIndex: 9999,
            display: 'flex', flexDirection: 'column',
            boxShadow: '-10px 0 40px rgba(0,0,0,0.5)',
            animation: 'slideInRight 0.3s ease-out'
        }}>
            <style>{`
                @keyframes slideInRight {
                    from { transform: translateX(100%); }
                    to { transform: translateX(0); }
                }
            `}</style>
            
            <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--separator)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <div style={{ fontSize: 10, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>Tool Inspector</div>
                    <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: 'var(--text-primary)' }}>{localTool.name}</h2>
                </div>
                <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: 24, padding: 0 }}>×</button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: 24 }}>
                <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 24, lineHeight: 1.5 }}>
                    {localTool.description}
                </p>

                {Object.keys(localTool)
                    .filter(key => Array.isArray(localTool[key]) && key !== 'dependencies' && key !== 'capabilities')
                    .map(key => (
                    <EditorList 
                        key={key}
                        label={key.replace(/([A-Z])/g, ' $1').trim()} 
                        items={localTool[key] || []} 
                        onChange={v => updateArray(key, v)} 
                        placeholder={`Add ${key.toLowerCase()}...`} 
                    />
                ))}
            </div>

            <div style={{ padding: 20, borderTop: '1px solid var(--separator)', background: 'var(--fill-quaternary)', display: 'flex', gap: 12, flexDirection: 'column' }}>
                <button 
                    onClick={handleSaveGlobal} 
                    disabled={saving || forking}
                    className="glass-btn glass-btn--primary" 
                    style={{ padding: '10px 16px', fontSize: 14, width: '100%', display: 'flex', justifyContent: 'center' }}
                >
                    {saving ? 'Saving...' : 'Save to Global Registry'}
                </button>
                <button 
                    onClick={handleFork} 
                    disabled={saving || forking}
                    className="glass-btn" 
                    style={{ padding: '10px 16px', fontSize: 14, width: '100%', display: 'flex', justifyContent: 'center' }}
                    title="Duplicate this tool to edit it safely just for this agent."
                >
                    {forking ? 'Forking...' : 'Fork & Assign Locally'}
                </button>
            </div>
        </div>
    );
};
