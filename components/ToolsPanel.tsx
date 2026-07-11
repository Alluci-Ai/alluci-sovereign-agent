import React, { useState } from 'react';
import { ToolManifest } from '../types';

interface ToolsPanelProps {
    tools: ToolManifest[];
    onSelect: (tool: ToolManifest) => void;
    onToggle: (id: string) => void;
    onDelete: (id: string) => void;
    onCreate: () => void;
    onImport?: (tool: Partial<ToolManifest>) => void;
}

export const ToolsPanel: React.FC<ToolsPanelProps> = ({
    tools,
    onSelect,
    onToggle,
    onDelete,
    onCreate,
    onImport
}) => {
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');

    const handleExport = (tool: ToolManifest) => {
        const exportable = JSON.parse(JSON.stringify(tool));
        if (exportable.execution) {
            delete exportable.execution.authHeadersVaultId;
            delete exportable.execution.envVarsVaultId;
        }
        const blob = new Blob([JSON.stringify(exportable, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${tool.id}_exported.stp`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            try {
                const parsed = JSON.parse(ev.target?.result as string);
                if (onImport) onImport(parsed);
            } catch(err) {
                alert('Invalid .stp package');
            }
        };
        reader.readAsText(file);
    };

    const checkStatus = (tool: ToolManifest) => {
        if (statusFilter === 'all') return true;
        if (statusFilter === 'active') return tool.enabled;
        if (statusFilter === 'error') return !tool.enabled;
        return true;
    };

    const displayTools = tools.filter(t => {
        const matchesSearch = t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            t.category.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesSearch && checkStatus(t);
    });

    const groupedTools = displayTools.reduce((acc, tool) => {
        const cat = tool.category || 'CUSTOM';
        if (!acc[cat]) acc[cat] = [];
        acc[cat].push(tool);
        return acc;
    }, {} as Record<string, ToolManifest[]>);

    return (
        <div style={{ maxWidth: 960, margin: '0 auto' }}>
            <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                marginBottom: 20, paddingBottom: 12,
                borderBottom: '1px solid var(--separator)',
            }}>
                <div className="flex flex-col gap-2">
                    <h2 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em', margin: 0 }}>Tool Adapters</h2>
                    <span className="text-[10px] uppercase font-mono tracking-widest text-text-tertiary">Tool Matrix Dashboard</span>
                </div>

                <div className="flex items-center gap-4">
                    <label className="glass-btn cursor-pointer" style={{ fontSize: 12, padding: '8px 16px', height: '100%', margin: 0 }}>
                        Import .stp
                        <input type="file" accept=".stp,.json" style={{ display: 'none' }} onChange={handleImport} />
                    </label>
                    <button onClick={onCreate} className="glass-btn glass-btn--primary" style={{ fontSize: 12, padding: '8px 16px', height: '100%' }}>
                        + Build Native Tool
                    </button>
                </div>
            </div>

            <div className="mb-6 relative z-10 w-full animate-in fade-in zoom-in-95 duration-200">
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <input 
                        type="text" 
                        placeholder="Search tools..." 
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="glass-input flex-1"
                        style={{ padding: '8px 12px', fontSize: 13 }}
                    />
                    <select 
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
                        className="glass-input"
                        style={{ padding: '8px 12px', fontSize: 13 }}
                    >
                        <option value="all">All Tools</option>
                        <option value="active">Active</option>
                        <option value="error">Disabled</option>
                    </select>
                </div>
            </div>

            {tools.length === 0 && (
                <div style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                    padding: '56px 20px', textAlign: 'center', color: 'var(--text-tertiary)',
                }}>
                    <p style={{ fontSize: 15, marginBottom: 8 }}>No tools loaded</p>
                    <p style={{ fontSize: 13 }}>Create a new tool to get started.</p>
                </div>
            )}

            <div className="flex flex-col gap-8">
                {Object.keys(groupedTools).length === 0 && tools.length > 0 && (
                    <div className="text-center py-12 text-[11px] font-mono text-text-tertiary">
                        NO_MATCHING_TOOLS_FOUND
                    </div>
                )}

                {Object.entries(groupedTools).map(([groupSource, groupArray]) => (
                    <div key={groupSource} className="flex flex-col gap-4">
                        <h3 className="glass-label text-[10px] tracking-widest opacity-60 m-0 uppercase flex items-center gap-2 border-b border-glass-edge pb-2">
                            {groupSource} TOOLS <span className="glass-tag tracking-normal text-[9px] bg-glass-1 shadow-none">{groupArray.length}</span>
                        </h3>

                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                            gap: 12,
                        }}>
                            {groupArray.map(tool => (
                                <div
                                    key={tool.id}
                                    onClick={() => onSelect(tool)}
                                    style={{
                                        background: 'var(--glass-bg)',
                                        border: `1px solid ${tool.enabled ? 'rgba(48,209,88,0.20)' : 'var(--separator)'}`,
                                        borderRadius: 14,
                                        padding: 16,
                                        cursor: 'pointer',
                                        transition: 'all 0.2s ease',
                                        opacity: tool.enabled ? 1 : 0.5,
                                        filter: tool.enabled ? 'none' : 'grayscale(0.6)',
                                        position: 'relative',
                                        overflow: 'hidden',
                                    }}
                                    className="hover:shadow-[0_0_20px_rgba(48,209,88,0.05)] hover:border-[rgba(48,209,88,0.3)] transition-all group"
                                >
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                                        <div>
                                            <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>{tool.name}</p>
                                            <p style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-quaternary)', textTransform: 'uppercase' }}>{tool.category} · {tool.id}</p>
                                        </div>
                                        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); handleExport(tool); }}
                                                className="opacity-0 group-hover:opacity-100 transition-opacity bg-transparent border-none text-accent text-sm p-1 hover:bg-accent/10 rounded"
                                                title="Export Sovereign Package (.stp)"
                                            >↓</button>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); onDelete(tool.id); }}
                                                className="opacity-0 group-hover:opacity-100 transition-opacity bg-transparent border-none text-status-error text-sm p-1 hover:bg-status-error/10 rounded"
                                            >✕</button>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); onToggle(tool.id); }}
                                                className={`glass-btn ${tool.enabled ? 'glass-btn--primary bg-status-good/10 text-status-good border-status-good/30' : ''}`}
                                                style={{ fontSize: 10, padding: '2px 8px', fontWeight: 500 }}
                                            >
                                                {tool.enabled ? 'Active' : 'Off'}
                                            </button>
                                        </div>
                                    </div>

                                    {tool.description && (
                                        <p style={{
                                            fontSize: 12, color: 'var(--text-tertiary)', lineHeight: 1.4,
                                            marginBottom: 10,
                                            display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                                        }}>{tool.description}</p>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

interface ToolDetailOverlayProps {
    tool: ToolManifest;
    onClose: () => void;
    onEdit?: (tool: ToolManifest) => void;
}

export const ToolDetailOverlay: React.FC<ToolDetailOverlayProps> = ({ tool, onClose, onEdit }) => {
    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 500,
            background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(8px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
        }} onClick={onClose}>
            <div style={{
                background: 'var(--bg-elevated)',
                borderRadius: 20, border: '1px solid var(--separator)',
                maxWidth: 720, width: '100%', maxHeight: '80vh',
                display: 'flex', flexDirection: 'column', overflow: 'hidden',
                boxShadow: 'var(--glass-shadow-lg)',
            }} onClick={e => e.stopPropagation()}>
                <div style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
                    padding: '20px 24px', borderBottom: '1px solid var(--separator)',
                }}>
                    <div>
                        <p style={{ fontSize: 11, fontWeight: 500, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>{tool.category}</p>
                        <h3 style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.01em' }}>{tool.name}</h3>
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <button onClick={() => onEdit && onEdit(tool)} className="glass-btn glass-btn--primary" style={{ fontSize: 12, padding: '4px 12px' }}>Edit Tool</button>
                        <button onClick={onClose} className="glass-btn" style={{ fontSize: 12, padding: '4px 12px' }}>Close</button>
                    </div>
                </div>

                <div style={{ flex: 1, overflowY: 'auto', padding: 24, display: 'flex', flexDirection: 'column', gap: 24 }} className="scrollbar-hide">
                    <section>
                        <h4 style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: 8 }}>Overview</h4>
                        <p style={{ fontSize: 14, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{tool.description}</p>
                    </section>

                    <section>
                        <h4 style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>JSON Parameters</h4>
                        <div style={{
                            padding: 14, borderRadius: 10,
                            background: 'var(--fill-quaternary)',
                            border: '1px solid var(--separator)',
                            fontFamily: 'var(--font-mono)', fontSize: 12,
                            whiteSpace: 'pre-wrap', color: 'var(--text-secondary)'
                        }}>
                            {tool.params || '{}'}
                        </div>
                    </section>
                </div>
            </div>
        </div>
    );
};
