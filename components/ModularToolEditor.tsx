import React, { useState } from 'react';
import { getCsrfToken } from '../csrfStore';
import { ReferenceDocsWidget } from './ReferenceDocsWidget';
import { PerToolKeyInput } from '../features/tools/PerToolKeyInput';
import { 
    Zap, 
    Layers, 
    Shield, 
    Key, 
    FileText, 
    Save, 
    GitFork, 
    Play, 
    Loader2, 
    Plus, 
    Trash2, 
    Sliders,
    X,
    Code2
} from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

// String Array Tag Editor for Permissions, Dependencies, etc.
const StringTagEditor: React.FC<{
    label: string;
    items: string[];
    onChange: (newItems: string[]) => void;
    placeholder: string;
    icon?: React.ReactNode;
}> = ({ label, items, onChange, placeholder, icon }) => {
    const [val, setVal] = useState('');
    const add = () => {
        if (!val.trim()) return;
        if (!items.includes(val.trim())) {
            onChange([...items, val.trim()]);
        }
        setVal('');
    };

    return (
        <div className="flex flex-col gap-2 mb-4">
            <label className="text-[10px] font-mono font-bold uppercase text-text-tertiary tracking-wider flex items-center gap-1.5">
                {icon} {label} ({items.length})
            </label>
            <div className="flex flex-wrap gap-1.5 min-h-[30px] p-2 rounded-lg bg-black/40 border border-white/10">
                {items.map((it, i) => (
                    <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-glass-1 border border-white/15 text-xs font-mono text-text-primary">
                        {it}
                        <button 
                            type="button"
                            onClick={() => onChange(items.filter((_, idx) => idx !== i))}
                            className="text-status-error hover:bg-status-error/10 rounded px-1 ml-0.5 text-xs"
                        >
                            ×
                        </button>
                    </span>
                ))}
                {items.length === 0 && (
                    <span className="text-[11px] text-text-quaternary font-mono italic">No items added yet.</span>
                )}
            </div>
            <div className="flex gap-2">
                <input
                    className="glass-input flex-1 px-3 py-1.5 text-xs font-mono"
                    value={val}
                    onChange={e => setVal(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), add())}
                    placeholder={placeholder}
                />
                <button type="button" onClick={add} className="glass-btn px-3 py-1 text-xs font-mono font-bold">
                    + Add
                </button>
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
    const [activeTab, setActiveTab] = useState<'general' | 'capabilities' | 'pcl' | 'dependencies' | 'keys' | 'docs'>('general');
    
    // Capability addition state
    const [newCapName, setNewCapName] = useState('');
    const [newCapType, setNewCapType] = useState('PYTHON_ASYNC');
    const [newCapDesc, setNewCapDesc] = useState('');

    const capabilitiesMap = typeof localTool.capabilities === 'object' && !Array.isArray(localTool.capabilities)
        ? localTool.capabilities
        : {};

    const handleAddCapability = () => {
        if (!newCapName.trim()) return;
        const updated = {
            ...capabilitiesMap,
            [newCapName.trim()]: {
                type: newCapType,
                description: newCapDesc.trim() || `Executes ${newCapName.trim()}`
            }
        };
        setLocalTool({ ...localTool, capabilities: updated });
        setNewCapName('');
        setNewCapDesc('');
    };

    const handleRemoveCapability = (capName: string) => {
        const updated = { ...capabilitiesMap };
        delete updated[capName];
        setLocalTool({ ...localTool, capabilities: updated });
    };

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
            position: 'fixed', top: 0, right: 0, bottom: 0, width: 560,
            background: 'var(--bg-glass-2)',
            backdropFilter: 'blur(35px) saturate(140%)',
            borderLeft: '1px solid var(--glass-edge)',
            zIndex: 9999,
            display: 'flex', flexDirection: 'column',
            boxShadow: '-15px 0 50px rgba(0,0,0,0.6)',
            animation: 'slideInRight 0.3s cubic-bezier(0.16, 1, 0.3, 1)'
        }}>
            <style>{`
                @keyframes slideInRight {
                    from { transform: translateX(100%); }
                    to { transform: translateX(0); }
                }
            `}</style>
            
            {/* Header */}
            <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--separator)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-accent/15 border border-accent/30 flex items-center justify-center text-accent">
                        <Sliders size={16} />
                    </div>
                    <div>
                        <div style={{ fontSize: 10, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 700 }}>
                            Tool Authoring & Inspector
                        </div>
                        <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: 'var(--text-primary)' }}>
                            {localTool.name}
                        </h2>
                    </div>
                </div>
                <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: 4 }}>
                    <X size={20} />
                </button>
            </div>

            {/* Sub-tabs inside Inspector */}
            <div className="flex gap-1 px-4 py-2 border-b border-glass-edge bg-black/20 overflow-x-auto">
                {[
                    { id: 'general', label: 'General', icon: <Sliders size={11} /> },
                    { id: 'capabilities', label: 'Capabilities', icon: <Zap size={11} /> },
                    { id: 'pcl', label: 'PCL & Permissions', icon: <Shield size={11} /> },
                    { id: 'dependencies', label: 'Dependencies', icon: <Layers size={11} /> },
                    { id: 'keys', label: 'Vault Keys', icon: <Key size={11} /> },
                    { id: 'docs', label: 'Docs', icon: <FileText size={11} /> },
                ].map(t => (
                    <button
                        key={t.id}
                        type="button"
                        onClick={() => setActiveTab(t.id as any)}
                        className={`glass-btn text-[11px] font-mono px-2.5 py-1 flex items-center gap-1.5 ${activeTab === t.id ? 'glass-btn--primary bg-accent/20 text-accent font-bold' : 'text-text-tertiary'}`}
                    >
                        {t.icon} {t.label}
                    </button>
                ))}
            </div>

            {/* Editor Body */}
            <div style={{ flex: 1, overflowY: 'auto', padding: 24 }} className="scrollbar-hide flex flex-col gap-5">
                
                {/* GENERAL TAB */}
                {activeTab === 'general' && (
                    <div className="flex flex-col gap-4 animate-in fade-in duration-200">
                        <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] font-mono uppercase text-text-tertiary tracking-wider font-bold">Tool Identifier (id)</label>
                            <input 
                                className="glass-input font-mono text-xs px-3 py-2 text-text-secondary bg-black/30"
                                value={localTool.id}
                                disabled
                            />
                        </div>

                        <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] font-mono uppercase text-text-tertiary tracking-wider font-bold">Tool Display Name</label>
                            <input 
                                className="glass-input font-mono text-xs px-3 py-2 text-text-primary"
                                value={localTool.name || ''}
                                onChange={e => setLocalTool({ ...localTool, name: e.target.value })}
                            />
                        </div>

                        <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] font-mono uppercase text-text-tertiary tracking-wider font-bold">Category</label>
                            <select 
                                className="glass-input text-xs px-3 py-2 font-mono"
                                value={localTool.category || 'TOOL'}
                                onChange={e => setLocalTool({ ...localTool, category: e.target.value })}
                            >
                                <option value="TOOL">TOOL (Native Engine)</option>
                                <option value="MCP">MCP (Model Context Protocol)</option>
                                <option value="API">API (REST / HTTP)</option>
                                <option value="CLI">CLI (Subprocess Exec)</option>
                                <option value="RPC">RPC (Attestation Bridge)</option>
                            </select>
                        </div>

                        <div className="flex flex-col gap-1.5">
                            <label className="text-[10px] font-mono uppercase text-text-tertiary tracking-wider font-bold">Description & System Instruction</label>
                            <textarea 
                                className="glass-input text-xs p-3 leading-relaxed font-sans"
                                rows={5}
                                value={localTool.description || ''}
                                onChange={e => setLocalTool({ ...localTool, description: e.target.value })}
                            />
                        </div>
                    </div>
                )}

                {/* CAPABILITIES TAB */}
                {activeTab === 'capabilities' && (
                    <div className="flex flex-col gap-4 animate-in fade-in duration-200">
                        <div className="flex items-center justify-between">
                            <label className="text-[10px] font-mono uppercase text-accent font-bold tracking-wider flex items-center gap-1.5">
                                <Zap size={12} /> Execution Capabilities ({Object.keys(capabilitiesMap).length})
                            </label>
                        </div>

                        {/* Existing Capabilities List */}
                        <div className="flex flex-col gap-2">
                            {Object.entries(capabilitiesMap).map(([cName, cDef]: [string, any]) => (
                                <div key={cName} className="p-3 rounded-lg bg-glass-1 border border-glass-edge flex items-center justify-between">
                                    <div className="flex flex-col gap-0.5">
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs font-mono font-bold text-text-primary">{cName}</span>
                                            <span className="text-[9px] font-mono uppercase px-1.5 py-0.2 rounded bg-white/5 text-text-tertiary">
                                                {cDef.type || 'NATIVE'}
                                            </span>
                                        </div>
                                        <span className="text-[10px] text-text-tertiary">{cDef.description || 'No description provided.'}</span>
                                    </div>
                                    <button 
                                        type="button"
                                        onClick={() => handleRemoveCapability(cName)}
                                        className="text-status-error hover:bg-status-error/10 p-1.5 rounded"
                                        title="Remove Capability"
                                    >
                                        <Trash2 size={13} />
                                    </button>
                                </div>
                            ))}
                        </div>

                        {/* Add New Capability Box */}
                        <div className="p-3.5 rounded-xl bg-black/40 border border-white/10 flex flex-col gap-2.5 mt-2">
                            <span className="text-[10px] font-mono uppercase text-text-tertiary font-bold tracking-wider flex items-center gap-1">
                                <Plus size={11} /> Add New Capability Binding
                            </span>
                            <div className="grid grid-cols-2 gap-2">
                                <input 
                                    className="glass-input font-mono text-xs px-2.5 py-1.5"
                                    placeholder="capability_name (e.g. format_code)"
                                    value={newCapName}
                                    onChange={e => setNewCapName(e.target.value)}
                                />
                                <select 
                                    className="glass-input font-mono text-xs px-2 py-1.5"
                                    value={newCapType}
                                    onChange={e => setNewCapType(e.target.value)}
                                >
                                    <option value="PYTHON_ASYNC">PYTHON_ASYNC</option>
                                    <option value="PYTHON_NATIVE">PYTHON_NATIVE</option>
                                    <option value="WEBSOCKET_EXEC_APPROVAL">WEBSOCKET_HITL</option>
                                    <option value="MCP">MCP_TOOL</option>
                                    <option value="CLI">CLI_SANDBOX</option>
                                    <option value="API">REST_API</option>
                                </select>
                            </div>
                            <input 
                                className="glass-input text-xs px-2.5 py-1.5"
                                placeholder="Capability summary / description..."
                                value={newCapDesc}
                                onChange={e => setNewCapDesc(e.target.value)}
                            />
                            <button 
                                type="button"
                                onClick={handleAddCapability}
                                className="glass-btn glass-btn--primary py-1.5 text-xs font-mono font-bold flex items-center justify-center gap-1.5"
                            >
                                <Plus size={12} /> Bind Capability
                            </button>
                        </div>
                    </div>
                )}

                {/* PCL & PERMISSIONS TAB */}
                {activeTab === 'pcl' && (
                    <div className="flex flex-col gap-4 animate-in fade-in duration-200">
                        <StringTagEditor 
                            label="Air-Gapped Permissions (PCL)"
                            items={localTool.permissions || []}
                            onChange={v => updateArray('permissions', v)}
                            placeholder="Add permission (e.g. filesystem_read, sandbox_exec)..."
                            icon={<Shield size={12} />}
                        />
                    </div>
                )}

                {/* DEPENDENCIES TAB */}
                {activeTab === 'dependencies' && (
                    <div className="flex flex-col gap-4 animate-in fade-in duration-200">
                        <StringTagEditor 
                            label="Runtime Dependencies"
                            items={localTool.dependencies || []}
                            onChange={v => updateArray('dependencies', v)}
                            placeholder="Add dependency (e.g. pyright, ruff, prettier)..."
                            icon={<Layers size={12} />}
                        />
                    </div>
                )}

                {/* VAULT KEYS TAB */}
                {activeTab === 'keys' && (
                    <div className="flex flex-col gap-4 animate-in fade-in duration-200">
                        <div className="flex flex-col gap-3">
                            <PerToolKeyInput 
                                toolId={localTool.id}
                                keyName="OPENCODE_API_KEY"
                                description="API token for external OpenCode providers or bridges"
                            />
                            <PerToolKeyInput 
                                toolId={localTool.id}
                                keyName="GITHUB_PERSONAL_ACCESS_TOKEN"
                                description="Personal access token for Git and GitHub MCP federation"
                            />
                        </div>
                    </div>
                )}

                {/* DOCS TAB */}
                {activeTab === 'docs' && (
                    <div className="flex flex-col gap-4 animate-in fade-in duration-200">
                        <ReferenceDocsWidget 
                            label="Reference Docs (.md paths or URLs)"
                            items={localTool.reference_docs || []} 
                            onChange={v => updateArray('reference_docs', v)} 
                            placeholder="Add local path or URL to .md file..." 
                        />
                    </div>
                )}

            </div>

            {/* Footer Action Buttons */}
            <div style={{ padding: 20, borderTop: '1px solid var(--separator)', background: 'var(--fill-quaternary)', display: 'flex', gap: 10, flexDirection: 'column' }}>
                <button 
                    onClick={handleSaveGlobal} 
                    disabled={saving || forking}
                    className="glass-btn glass-btn--primary py-2.5 text-xs font-mono font-bold flex items-center justify-center gap-2"
                >
                    {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
                    {saving ? 'Persisting to Registry...' : 'Save to Global Registry'}
                </button>
                <button 
                    onClick={handleFork} 
                    disabled={saving || forking}
                    className="glass-btn py-2.5 text-xs font-mono font-bold flex items-center justify-center gap-2"
                    title="Duplicate this tool to edit it safely just for this agent."
                >
                    {forking ? <Loader2 size={13} className="animate-spin" /> : <GitFork size={13} />}
                    {forking ? 'Forking Tool...' : 'Fork & Assign Locally'}
                </button>
            </div>
        </div>
    );
};
