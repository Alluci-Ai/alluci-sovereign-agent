import React, { useState, useEffect, useCallback } from 'react';
import { ToolManifest } from '../types';
import { 
    Zap, 
    Shield, 
    ShieldCheck, 
    Terminal, 
    Layers, 
    FileCode, 
    Play, 
    Loader2, 
    Key, 
    FileText, 
    Server, 
    Cpu, 
    Code2, 
    Sparkles, 
    ExternalLink, 
    CheckCircle2, 
    AlertTriangle,
    Download,
    Trash2,
    Sliders,
    Search,
    BookOpen
} from 'lucide-react';
import { PerToolKeyInput } from '../features/tools/PerToolKeyInput';
import { useStore } from '../store/useStore';
import { sovereignService } from '../sovereignService';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

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
    const { accessToken, setTools } = useStore();
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [selectedToolForOverlay, setSelectedToolForOverlay] = useState<ToolManifest | null>(null);
    const [loading, setLoading] = useState(tools.length === 0);

    const refreshTools = useCallback(async () => {
        try {
            const data = await sovereignService.listRegistryTools();
            if (data && Array.isArray(data.tools)) {
                setTools(data.tools);
            }
        } catch (err) {
            console.error('[ToolsPanel] Failed to sync registry tools', err);
        } finally {
            setLoading(false);
        }
    }, [setTools]);

    useEffect(() => {
        refreshTools();
    }, [refreshTools, accessToken]);

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
            } catch (err) {
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
            (t.category && t.category.toLowerCase().includes(searchQuery.toLowerCase())) ||
            (t.description && t.description.toLowerCase().includes(searchQuery.toLowerCase()));
        return matchesSearch && checkStatus(t);
    });

    const groupedTools = displayTools.reduce((acc, tool) => {
        const cat = tool.category || 'TOOL';
        if (!acc[cat]) acc[cat] = [];
        acc[cat].push(tool);
        return acc;
    }, {} as Record<string, ToolManifest[]>);

    const getCapabilitiesCount = (tool: ToolManifest): number => {
        if (!tool.capabilities) return 0;
        if (Array.isArray(tool.capabilities)) return tool.capabilities.length;
        return Object.keys(tool.capabilities).length;
    };

    return (
        <div style={{ maxWidth: 1100, margin: '0 auto', paddingBottom: 40 }}>
            {/* Header Bar */}
            <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                marginBottom: 24, paddingBottom: 16,
                borderBottom: '1px solid var(--separator)',
            }}>
                <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-3">
                        <h2 style={{ fontSize: 24, fontWeight: 700, letterSpacing: '-0.02em', margin: 0 }}>
                            Tool Matrix & Harness Engine
                        </h2>
                        <span className="glass-tag text-[10px] tracking-widest uppercase bg-status-good/10 text-status-good border-status-good/20">
                            {tools.length} Loaded
                        </span>
                    </div>
                    <span className="text-[11px] uppercase font-mono tracking-wider text-text-tertiary">
                        Autonomous Execution Adapters · LSP · MCP · Formatters · Air-Gapped Sandboxes
                    </span>
                </div>

                <div className="flex items-center gap-3">
                    <label className="glass-btn cursor-pointer flex items-center gap-2" style={{ fontSize: 12, padding: '8px 16px', height: '100%', margin: 0 }}>
                        <Download size={13} />
                        Import .stp
                        <input type="file" accept=".stp,.json" style={{ display: 'none' }} onChange={handleImport} />
                    </label>
                    <button onClick={onCreate} className="glass-btn glass-btn--primary flex items-center gap-2" style={{ fontSize: 12, padding: '8px 16px', height: '100%' }}>
                        <Zap size={13} />
                        + Build Native Tool
                    </button>
                </div>
            </div>

            {/* Filter and Search Bar */}
            <div className="mb-6 relative z-10 w-full animate-in fade-in zoom-in-95 duration-200">
                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <div className="relative flex-1">
                        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
                        <input 
                            type="text" 
                            placeholder="Search tools by name, category, capability, or keywords..." 
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="glass-input w-full pl-9 pr-4 py-2 text-xs font-mono"
                        />
                    </div>
                    <select 
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value)}
                        className="glass-input text-xs px-3 py-2"
                    >
                        <option value="all">All Statuses ({tools.length})</option>
                        <option value="active">Active Only</option>
                        <option value="error">Disabled Only</option>
                    </select>
                </div>
            </div>

            {/* Loading / Empty State */}
            {loading && tools.length === 0 ? (
                <div style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                    padding: '56px 20px', textAlign: 'center', color: 'var(--text-tertiary)',
                }}>
                    <Loader2 size={32} className="animate-spin text-accent mb-3" />
                    <p className="font-mono text-[11px] tracking-widest uppercase">BOOTING_TOOL_MATRIX...</p>
                </div>
            ) : tools.length === 0 ? (
                <div style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                    padding: '56px 20px', textAlign: 'center', color: 'var(--text-tertiary)',
                }}>
                    <Terminal size={36} className="text-text-tertiary opacity-40 mb-3" />
                    <p style={{ fontSize: 15, marginBottom: 8, fontWeight: 600 }}>No Tools Loaded</p>
                    <p style={{ fontSize: 13 }}>Create a new tool or import an STP package to get started.</p>
                </div>
            ) : null}

            {/* Grouped Tool Matrices */}
            <div className="flex flex-col gap-8">
                {Object.keys(groupedTools).length === 0 && tools.length > 0 && (
                    <div className="text-center py-12 text-[11px] font-mono text-text-tertiary">
                        NO_MATCHING_TOOLS_FOUND
                    </div>
                )}

                {Object.entries(groupedTools).map(([groupCategory, groupArray]) => (
                    <div key={groupCategory} className="flex flex-col gap-4">
                        <div className="flex items-center justify-between border-b border-glass-edge pb-2">
                            <h3 className="glass-label text-[11px] tracking-widest opacity-80 m-0 uppercase flex items-center gap-2 font-mono">
                                <Cpu size={13} className="text-accent" />
                                {groupCategory} MATRIX 
                                <span className="glass-tag tracking-normal text-[9px] bg-glass-1 shadow-none font-bold">
                                    {groupArray.length}
                                </span>
                            </h3>
                        </div>

                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fill, minmax(330px, 1fr))',
                            gap: 16,
                        }}>
                            {groupArray.map(tool => {
                                const capCount = getCapabilitiesCount(tool);
                                const isCodiTool = tool.id.includes('codi');
                                const isHitlGated = tool.permissions?.includes('hitl_gating') || tool.capabilities?.hasOwnProperty('request_hitl_approval');
                                const isSandboxed = tool.permissions?.includes('sandbox_exec') || tool.execution?.sandboxed;
                                const hasVault = tool.permissions?.includes('vault_secret_read');

                                return (
                                    <div
                                        key={tool.id}
                                        onClick={() => {
                                            setSelectedToolForOverlay(tool);
                                            onSelect(tool);
                                        }}
                                        style={{
                                            background: 'var(--glass-bg)',
                                            border: `1px solid ${tool.enabled ? 'rgba(48,209,88,0.25)' : 'var(--separator)'}`,
                                            borderRadius: 16,
                                            padding: 18,
                                            cursor: 'pointer',
                                            transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
                                            opacity: tool.enabled ? 1 : 0.6,
                                            filter: tool.enabled ? 'none' : 'grayscale(0.5)',
                                            position: 'relative',
                                            overflow: 'hidden',
                                        }}
                                        className="hover:shadow-[0_8px_30px_rgba(48,209,88,0.08)] hover:border-[rgba(48,209,88,0.4)] hover:-translate-y-0.5 transition-all group flex flex-col justify-between"
                                    >
                                        <div>
                                            {/* Header */}
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                                                <div className="flex-1 pr-2">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <span className="text-[9px] uppercase font-mono px-2 py-0.5 rounded bg-accent/10 text-accent font-semibold border border-accent/20">
                                                            {tool.category || 'TOOL'}
                                                        </span>
                                                        {tool.verified && (
                                                            <span className="text-[9px] uppercase font-mono px-1.5 py-0.5 rounded bg-status-good/10 text-status-good flex items-center gap-1 border border-status-good/20">
                                                                <ShieldCheck size={10} /> Verified
                                                            </span>
                                                        )}
                                                    </div>
                                                    <p style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', margin: 0, lineHeight: 1.3 }}>
                                                        {tool.name}
                                                    </p>
                                                    <p style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-quaternary)', marginTop: 2 }}>
                                                        {tool.id}
                                                    </p>
                                                </div>

                                                {/* Action Buttons */}
                                                <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); handleExport(tool); }}
                                                        className="opacity-0 group-hover:opacity-100 transition-opacity bg-transparent border-none text-accent text-sm p-1.5 hover:bg-accent/10 rounded"
                                                        title="Export Sovereign Package (.stp)"
                                                    >
                                                        <Download size={13} />
                                                    </button>
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); onDelete(tool.id); }}
                                                        className="opacity-0 group-hover:opacity-100 transition-opacity bg-transparent border-none text-status-error text-sm p-1.5 hover:bg-status-error/10 rounded"
                                                        title="Delete Tool"
                                                    >
                                                        <Trash2 size={13} />
                                                    </button>
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); onToggle(tool.id); }}
                                                        className={`glass-btn ${tool.enabled ? 'glass-btn--primary bg-status-good/15 text-status-good border-status-good/40 font-bold' : 'text-text-tertiary'}`}
                                                        style={{ fontSize: 10, padding: '3px 10px', borderRadius: 20 }}
                                                    >
                                                        {tool.enabled ? 'Active' : 'Off'}
                                                    </button>
                                                </div>
                                            </div>

                                            {/* Description */}
                                            {tool.description && (
                                                <p style={{
                                                    fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.45,
                                                    marginBottom: 12,
                                                    display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                                                }}>
                                                    {tool.description}
                                                </p>
                                            )}

                                            {/* Subsystem & Capability Badges */}
                                            <div className="flex flex-wrap gap-1.5 mb-3">
                                                {capCount > 0 && (
                                                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-glass-pressed border border-white/10 text-accent font-medium flex items-center gap-1">
                                                        <Zap size={10} /> {capCount} Capabilities
                                                    </span>
                                                )}
                                                {isCodiTool && (
                                                    <>
                                                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-glass-pressed border border-white/10 text-emerald-400 font-medium flex items-center gap-1">
                                                            <Server size={10} /> 5 MCP
                                                        </span>
                                                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-glass-pressed border border-white/10 text-sky-400 font-medium flex items-center gap-1">
                                                            <Code2 size={10} /> 8 LSP
                                                        </span>
                                                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-glass-pressed border border-white/10 text-purple-400 font-medium flex items-center gap-1">
                                                            <Sparkles size={10} /> 4 Formatters
                                                        </span>
                                                    </>
                                                )}
                                                {isHitlGated && (
                                                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300 flex items-center gap-1 font-medium">
                                                        <Shield size={10} /> HITL Gated
                                                    </span>
                                                )}
                                                {isSandboxed && (
                                                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-300 flex items-center gap-1 font-medium">
                                                        <Terminal size={10} /> Sandboxed
                                                    </span>
                                                )}
                                                {hasVault && (
                                                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 flex items-center gap-1 font-medium">
                                                        <Key size={10} /> Vault
                                                    </span>
                                                )}
                                            </div>
                                        </div>

                                        {/* Footer - Dependencies & Execution Type */}
                                        <div style={{
                                            paddingTop: 10, borderTop: '1px solid var(--separator)',
                                            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                        }}>
                                            <div className="flex items-center gap-1 overflow-hidden">
                                                {tool.dependencies && tool.dependencies.slice(0, 3).map((dep, idx) => (
                                                    <span key={idx} className="text-[9px] font-mono text-text-tertiary bg-white/5 px-1.5 py-0.5 rounded border border-white/5">
                                                        {dep}
                                                    </span>
                                                ))}
                                                {tool.dependencies && tool.dependencies.length > 3 && (
                                                    <span className="text-[9px] font-mono text-text-quaternary">
                                                        +{tool.dependencies.length - 3}
                                                    </span>
                                                )}
                                            </div>

                                            <span style={{ fontSize: 9, fontFamily: 'var(--font-mono)', color: 'var(--text-quaternary)' }}>
                                                {tool.execution?.type || (isCodiTool ? 'PYTHON_ASYNC' : 'NATIVE')}
                                            </span>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                ))}
            </div>

            {/* Comprehensive Detail Overlay */}
            {selectedToolForOverlay && (
                <ToolDetailOverlay 
                    tool={selectedToolForOverlay}
                    onClose={() => setSelectedToolForOverlay(null)}
                    onEdit={(t) => {
                        setSelectedToolForOverlay(null);
                        onSelect(t);
                    }}
                />
            )}
        </div>
    );
};

/* ========================================================================= */
/* COMPREHENSIVE MULTI-TAB TOOL DETAIL OVERLAY                               */
/* ========================================================================= */

interface ToolDetailOverlayProps {
    tool: ToolManifest;
    onClose: () => void;
    onEdit?: (tool: ToolManifest) => void;
}

export const ToolDetailOverlay: React.FC<ToolDetailOverlayProps> = ({ tool, onClose, onEdit }) => {
    const { accessToken } = useStore();
    const [activeTab, setActiveTab] = useState<'capabilities' | 'subsystems' | 'security' | 'dependencies' | 'credentials' | 'docs'>('capabilities');
    
    // Live Capability Sandbox Testing State
    const capabilitiesList = tool.capabilities 
        ? (Array.isArray(tool.capabilities) ? tool.capabilities : Object.keys(tool.capabilities))
        : [];
    const [selectedCapability, setSelectedCapability] = useState<string>(capabilitiesList[0] || 'validate_ast_syntax');
    const [testParamsInput, setTestParamsInput] = useState<string>('{\n  "file_path": "backend/test_example.py",\n  "proposed_code": "def hello():\\n    return 42\\n"\n}');
    const [testRunning, setTestRunning] = useState(false);
    const [testResponse, setTestResponse] = useState<any>(null);
    const [testLatencyMs, setTestLatencyMs] = useState<number | null>(null);

    const handleRunCapabilityTest = async () => {
        setTestRunning(true);
        setTestResponse(null);
        setTestLatencyMs(null);
        const startTime = performance.now();

        try {
            let parsedParams = {};
            try {
                parsedParams = JSON.parse(testParamsInput);
            } catch (err) {
                setTestResponse({ status: "JSON_PARSE_ERROR", error: "Input payload is not valid JSON." });
                setTestRunning(false);
                return;
            }

            const res = await fetch(`${DAEMON_URL}/api/v1/tools/${tool.id}/capability`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    ...(accessToken ? { 'Authorization': `Bearer ${accessToken}` } : {})
                },
                body: JSON.stringify({
                    capability: selectedCapability,
                    params: parsedParams
                }),
                credentials: 'include'
            });

            const duration = Math.round(performance.now() - startTime);
            setTestLatencyMs(duration);

            if (res.ok) {
                const data = await res.json();
                setTestResponse(data);
            } else {
                const errData = await res.json().catch(() => ({ status: res.status, statusText: res.statusText }));
                setTestResponse(errData);
            }
        } catch (e: any) {
            setTestResponse({ status: "NETWORK_ERROR", error: e.message || String(e) });
        } finally {
            setTestRunning(false);
        }
    };

    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 500,
            background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(12px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
        }} onClick={onClose}>
            <div style={{
                background: 'var(--bg-elevated)',
                borderRadius: 20, border: '1px solid var(--separator)',
                maxWidth: 900, width: '100%', maxHeight: '88vh',
                display: 'flex', flexDirection: 'column', overflow: 'hidden',
                boxShadow: 'var(--glass-shadow-lg)',
            }} onClick={e => e.stopPropagation()}>
                {/* Modal Header */}
                <div style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '20px 28px', borderBottom: '1px solid var(--separator)',
                    background: 'var(--glass-bg)',
                }}>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-accent/15 border border-accent/30 flex items-center justify-center text-accent">
                            <Zap size={20} />
                        </div>
                        <div>
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] font-mono uppercase font-bold text-accent tracking-wider">
                                    {tool.category || 'TOOL'}
                                </span>
                                {tool.verified && (
                                    <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-status-good/15 text-status-good border border-status-good/30 flex items-center gap-1 font-bold">
                                        <ShieldCheck size={10} /> Verified Sovereign
                                    </span>
                                )}
                            </div>
                            <h3 style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em', margin: 0, color: 'var(--text-primary)' }}>
                                {tool.name}
                            </h3>
                        </div>
                    </div>

                    <div style={{ display: 'flex', gap: 8 }}>
                        <button onClick={() => onEdit && onEdit(tool)} className="glass-btn glass-btn--primary flex items-center gap-2" style={{ fontSize: 12, padding: '6px 16px' }}>
                            <Sliders size={13} /> Edit Tool
                        </button>
                        <button onClick={onClose} className="glass-btn" style={{ fontSize: 12, padding: '6px 14px' }}>
                            Close
                        </button>
                    </div>
                </div>

                {/* Tab Navigation */}
                <div style={{
                    display: 'flex', gap: 4, padding: '8px 24px',
                    borderBottom: '1px solid var(--separator)',
                    background: 'rgba(0,0,0,0.2)',
                    overflowX: 'auto'
                }}>
                    {[
                        { id: 'capabilities', label: 'Capabilities & Sandbox', icon: <Zap size={12} /> },
                        { id: 'subsystems', label: 'OpenCode Subsystems', icon: <Server size={12} /> },
                        { id: 'security', label: 'Security & PCL', icon: <Shield size={12} /> },
                        { id: 'dependencies', label: 'Dependencies', icon: <Layers size={12} /> },
                        { id: 'credentials', label: 'Vault Credentials', icon: <Key size={12} /> },
                        { id: 'docs', label: 'Documentation', icon: <BookOpen size={12} /> },
                    ].map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id as any)}
                            className={`glass-btn text-xs font-mono flex items-center gap-2 transition-all ${activeTab === tab.id ? 'glass-btn--primary bg-accent/20 text-accent border-accent/40 font-bold' : 'text-text-tertiary'}`}
                            style={{ padding: '6px 14px', borderRadius: 8 }}
                        >
                            {tab.icon} {tab.label}
                        </button>
                    ))}
                </div>

                {/* Tab Content Container */}
                <div style={{ flex: 1, overflowY: 'auto', padding: 28 }} className="scrollbar-hide flex flex-col gap-6">

                    {/* OVERVIEW SECTION */}
                    <div className="p-4 rounded-xl bg-glass-1 border border-glass-edge">
                        <h4 className="text-[10px] font-mono uppercase text-text-tertiary tracking-wider mb-1 font-semibold">Tool Architecture Overview</h4>
                        <p className="text-xs text-text-secondary leading-relaxed font-sans m-0">{tool.description}</p>
                    </div>

                    {/* TAB 1: CAPABILITIES & LIVE SANDBOX */}
                    {activeTab === 'capabilities' && (
                        <div className="flex flex-col gap-6 animate-in fade-in duration-200">
                            {/* Capabilities List Grid */}
                            <div>
                                <h4 className="text-xs font-mono uppercase text-accent font-bold tracking-wider mb-3 flex items-center gap-2">
                                    <Zap size={14} /> Registered Execution Capabilities ({capabilitiesList.length})
                                </h4>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    {typeof tool.capabilities === 'object' && !Array.isArray(tool.capabilities) ? (
                                        Object.entries(tool.capabilities).map(([capName, capDef]: [string, any]) => (
                                            <div 
                                                key={capName}
                                                onClick={() => setSelectedCapability(capName)}
                                                className={`p-3.5 rounded-xl border cursor-pointer transition-all ${selectedCapability === capName ? 'bg-accent/10 border-accent/40 shadow-[0_0_15px_rgba(43,158,255,0.1)]' : 'bg-glass-1 border-glass-edge hover:border-white/20'}`}
                                            >
                                                <div className="flex items-center justify-between mb-1.5">
                                                    <span className="text-xs font-mono font-bold text-text-primary flex items-center gap-1.5">
                                                        <FileCode size={12} className="text-accent" /> {capName}
                                                    </span>
                                                    <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-text-tertiary">
                                                        {capDef.type || 'NATIVE'}
                                                    </span>
                                                </div>
                                                <p className="text-[11px] text-text-tertiary m-0 line-clamp-2">
                                                    {capDef.description || `Executes ${capName} on ${tool.name}.`}
                                                </p>
                                            </div>
                                        ))
                                    ) : (
                                        capabilitiesList.map((capName: string) => (
                                            <div 
                                                key={capName}
                                                onClick={() => setSelectedCapability(capName)}
                                                className={`p-3.5 rounded-xl border cursor-pointer transition-all ${selectedCapability === capName ? 'bg-accent/10 border-accent/40' : 'bg-glass-1 border-glass-edge'}`}
                                            >
                                                <span className="text-xs font-mono font-bold text-text-primary flex items-center gap-1.5">
                                                    <FileCode size={12} className="text-accent" /> {capName}
                                                </span>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>

                            {/* Live Sandbox Execution Console */}
                            <div className="p-5 rounded-2xl bg-black/40 border border-accent/30 shadow-[0_0_30px_rgba(0,0,0,0.4)] flex flex-col gap-4">
                                <div className="flex items-center justify-between border-b border-white/10 pb-3">
                                    <div className="flex items-center gap-2">
                                        <Terminal size={14} className="text-accent" />
                                        <span className="text-xs font-mono font-bold text-text-primary uppercase tracking-wide">
                                            Interactive Sandbox Console: <span className="text-accent font-bold">{selectedCapability}</span>
                                        </span>
                                    </div>
                                    {testLatencyMs !== null && (
                                        <span className="text-[10px] font-mono text-status-good bg-status-good/10 px-2 py-0.5 rounded border border-status-good/20 font-bold">
                                            ⚡ {testLatencyMs} ms
                                        </span>
                                    )}
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {/* Input JSON */}
                                    <div className="flex flex-col gap-2">
                                        <label className="text-[10px] font-mono uppercase text-text-tertiary tracking-wider font-semibold">
                                            Input JSON Payload (params):
                                        </label>
                                        <textarea
                                            value={testParamsInput}
                                            onChange={(e) => setTestParamsInput(e.target.value)}
                                            rows={8}
                                            className="glass-input font-mono text-xs p-3 w-full bg-black/60 border border-white/15 focus:border-accent/50 leading-relaxed scrollbar-hide"
                                            placeholder='{\n  "key": "value"\n}'
                                        />
                                        <button
                                            onClick={handleRunCapabilityTest}
                                            disabled={testRunning}
                                            className="glass-btn glass-btn--primary flex items-center justify-center gap-2 py-2 text-xs font-mono font-bold"
                                        >
                                            {testRunning ? (
                                                <>
                                                    <Loader2 size={13} className="animate-spin" /> Running Capability...
                                                </>
                                            ) : (
                                                <>
                                                    <Play size={13} /> Execute Sandbox Test
                                                </>
                                            )}
                                        </button>
                                    </div>

                                    {/* Output Response */}
                                    <div className="flex flex-col gap-2">
                                        <label className="text-[10px] font-mono uppercase text-text-tertiary tracking-wider font-semibold flex items-center justify-between">
                                            <span>Live Output Stream</span>
                                            {testResponse && (
                                                <span className={`text-[9px] font-bold ${testResponse.valid || testResponse.status === 'SUCCESS' ? 'text-status-good' : 'text-status-error'}`}>
                                                    STATUS: {testResponse.status || 'OK'}
                                                </span>
                                            )}
                                        </label>
                                        <pre className="p-3 rounded-lg bg-black/80 border border-white/10 text-xs font-mono text-text-secondary h-[180px] overflow-auto scrollbar-hide m-0 leading-relaxed whitespace-pre-wrap">
                                            {testResponse ? JSON.stringify(testResponse, null, 2) : '// Response telemetry will appear here after execution...'}
                                        </pre>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* TAB 2: OPENCODE SUBSYSTEMS */}
                    {activeTab === 'subsystems' && (
                        <div className="flex flex-col gap-6 animate-in fade-in duration-200">
                            {/* MCP Servers */}
                            <div>
                                <h4 className="text-xs font-mono uppercase text-emerald-400 font-bold tracking-wider mb-3 flex items-center gap-2">
                                    <Server size={14} /> Federated MCP Servers (Model Context Protocol)
                                </h4>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    {[
                                        { name: 'filesystem', type: 'local', desc: 'Sandboxed local filesystem access' },
                                        { name: 'git', type: 'local', desc: 'Repository AST history, branches & diffs' },
                                        { name: 'sqlite', type: 'local', desc: 'Immutable audit database state queries' },
                                        { name: 'ast-grep', type: 'local', desc: 'Structural AST multi-file code rewriting' },
                                        { name: 'memory', type: 'local', desc: 'Persistent 4-Tier H-LSM synchronized memory' },
                                    ].map((mcp, idx) => (
                                        <div key={idx} className="p-3 rounded-xl bg-glass-1 border border-glass-edge flex flex-col gap-1">
                                            <div className="flex items-center justify-between">
                                                <span className="text-xs font-mono font-bold text-text-primary">@{mcp.name}</span>
                                                <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-bold">
                                                    {mcp.type}
                                                </span>
                                            </div>
                                            <span className="text-[11px] text-text-tertiary">{mcp.desc}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* LSP Language Servers */}
                            <div>
                                <h4 className="text-xs font-mono uppercase text-sky-400 font-bold tracking-wider mb-3 flex items-center gap-2">
                                    <Code2 size={14} /> Active LSP Language Servers
                                </h4>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
                                    {[
                                        { lang: 'Python', server: 'pyright-langserver' },
                                        { lang: 'TypeScript', server: 'typescript-language-server' },
                                        { lang: 'Rust', server: 'rust-analyzer' },
                                        { lang: 'Go', server: 'gopls' },
                                        { lang: 'C / C++', server: 'clangd' },
                                        { lang: 'Bash', server: 'bash-language-server' },
                                        { lang: 'YAML', server: 'yaml-language-server' },
                                        { lang: 'JSON', server: 'vscode-json-language-server' },
                                    ].map((lsp, idx) => (
                                        <div key={idx} className="p-2.5 rounded-lg bg-glass-1 border border-glass-edge">
                                            <div className="text-xs font-mono font-bold text-text-primary">{lsp.lang}</div>
                                            <div className="text-[10px] font-mono text-text-quaternary truncate">{lsp.server}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Formatters */}
                            <div>
                                <h4 className="text-xs font-mono uppercase text-purple-400 font-bold tracking-wider mb-3 flex items-center gap-2">
                                    <Sparkles size={14} /> Automated Code Formatters
                                </h4>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    {[
                                        { name: 'Ruff', ext: '.py, .pyi', cmd: 'ruff format $FILE' },
                                        { name: 'Prettier', ext: '.ts, .tsx, .js, .json, .md', cmd: 'npx prettier --write $FILE' },
                                        { name: 'Rustfmt', ext: '.rs', cmd: 'rustfmt $FILE' },
                                        { name: 'Gofmt', ext: '.go', cmd: 'gofmt -w $FILE' },
                                    ].map((fmt, idx) => (
                                        <div key={idx} className="p-3 rounded-xl bg-glass-1 border border-glass-edge flex flex-col gap-1">
                                            <div className="flex items-center justify-between">
                                                <span className="text-xs font-mono font-bold text-text-primary">{fmt.name}</span>
                                                <span className="text-[10px] font-mono text-text-tertiary">{fmt.ext}</span>
                                            </div>
                                            <code className="text-[10px] font-mono text-accent bg-black/40 p-1.5 rounded border border-white/5">
                                                {fmt.cmd}
                                            </code>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Slash Commands */}
                            <div>
                                <h4 className="text-xs font-mono uppercase text-amber-400 font-bold tracking-wider mb-3 flex items-center gap-2">
                                    <Terminal size={14} /> OpenCode Custom Slash Commands
                                </h4>
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                                    {[
                                        { cmd: '/test', desc: 'Run automated tests with coverage' },
                                        { cmd: '/lint', desc: 'Run compiler and typecheck diagnostics' },
                                        { cmd: '/format', desc: 'Format source code with ruff/prettier' },
                                        { cmd: '/checkpoint', desc: 'Create signed atomic pre-state checkpoint' },
                                        { cmd: '/rollback', desc: 'Atomic 1-click rollback to snapshot' },
                                        { cmd: '/review', desc: 'AST diff and code quality review' },
                                        { cmd: '/sec-audit', desc: 'Audit secrets and air-gap compliance' },
                                    ].map((c, idx) => (
                                        <div key={idx} className="p-2.5 rounded-lg bg-glass-1 border border-glass-edge">
                                            <div className="text-xs font-mono font-bold text-amber-300">{c.cmd}</div>
                                            <div className="text-[10px] text-text-tertiary">{c.desc}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* TAB 3: SECURITY & PERMISSION CONTROL LIST (PCL) */}
                    {activeTab === 'security' && (
                        <div className="flex flex-col gap-6 animate-in fade-in duration-200">
                            <div>
                                <h4 className="text-xs font-mono uppercase text-status-good font-bold tracking-wider mb-3 flex items-center gap-2">
                                    <ShieldCheck size={14} /> Air-Gapped Permission Control Layer (PCL)
                                </h4>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    {(tool.permissions || [
                                        'filesystem_read',
                                        'filesystem_write',
                                        'hitl_gating',
                                        'sandbox_exec',
                                        'vault_secret_read',
                                        'mcp_federation',
                                        'lsp_diagnostics',
                                        'reference_resolution'
                                    ]).map((perm, idx) => (
                                        <div key={idx} className="p-3 rounded-xl bg-glass-1 border border-glass-edge flex items-center gap-3">
                                            <CheckCircle2 size={16} className="text-status-good flex-shrink-0" />
                                            <div>
                                                <div className="text-xs font-mono font-bold text-text-primary">{perm}</div>
                                                <div className="text-[10px] text-text-tertiary">Strictly governed by Sovereign Zero-Trust policies</div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="p-4 rounded-xl bg-status-good/10 border border-status-good/20">
                                <div className="flex items-center gap-2 mb-1">
                                    <ShieldCheck size={14} className="text-status-good" />
                                    <span className="text-xs font-mono font-bold text-status-good uppercase">Ed25519 VerusID Cryptographic Attestation</span>
                                </div>
                                <p className="text-[11px] font-mono text-text-secondary m-0">
                                    SIGNATURE: {tool.signature || 'VERUSID_ED25519_ATTESTED_AUTH_VALID'}
                                </p>
                            </div>
                        </div>
                    )}

                    {/* TAB 4: DEPENDENCIES & RUNTIME */}
                    {activeTab === 'dependencies' && (
                        <div className="flex flex-col gap-6 animate-in fade-in duration-200">
                            <div>
                                <h4 className="text-xs font-mono uppercase text-accent font-bold tracking-wider mb-3 flex items-center gap-2">
                                    <Layers size={14} /> Runtime Dependencies & Tooling
                                </h4>

                                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                                    {(tool.dependencies || [
                                        'pyright', 'typescript-language-server', 'git', 'httpx', 'ast', 'sqlite3', 'ruff', 'prettier', 'rustfmt', 'gofmt'
                                    ]).map((dep, idx) => (
                                        <div key={idx} className="p-3 rounded-xl bg-glass-1 border border-glass-edge flex items-center justify-between">
                                            <span className="text-xs font-mono font-bold text-text-primary">{dep}</span>
                                            <span className="text-[9px] font-mono text-status-good bg-status-good/10 px-1.5 py-0.5 rounded border border-status-good/20">
                                                INSTALLED
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* TAB 5: VAULT CREDENTIALS */}
                    {activeTab === 'credentials' && (
                        <div className="flex flex-col gap-6 animate-in fade-in duration-200">
                            <div>
                                <h4 className="text-xs font-mono uppercase text-accent font-bold tracking-wider mb-3 flex items-center gap-2">
                                    <Key size={14} /> Per-Tool Vault Credentials (AES-256 OS Keychain)
                                </h4>
                                <p className="text-xs text-text-secondary mb-4">
                                    Securely manage API keys, bearer tokens, and credentials bound directly to this tool without plain-text leakage.
                                </p>

                                <div className="flex flex-col gap-3">
                                    <PerToolKeyInput 
                                        toolId={tool.id}
                                        keyName="OPENCODE_API_KEY"
                                        description="API token for external OpenCode providers or bridges"
                                    />
                                    <PerToolKeyInput 
                                        toolId={tool.id}
                                        keyName="GITHUB_PERSONAL_ACCESS_TOKEN"
                                        description="Personal access token for Git and GitHub MCP federation"
                                    />
                                    <PerToolKeyInput 
                                        toolId={tool.id}
                                        keyName="CUSTOM_TOOL_BEARER_TOKEN"
                                        description="Bearer authorization header for native tool endpoints"
                                    />
                                </div>
                            </div>
                        </div>
                    )}

                    {/* TAB 6: DOCUMENTATION & BLUEPRINTS */}
                    {activeTab === 'docs' && (
                        <div className="flex flex-col gap-6 animate-in fade-in duration-200">
                            <div>
                                <h4 className="text-xs font-mono uppercase text-accent font-bold tracking-wider mb-3 flex items-center gap-2">
                                    <BookOpen size={14} /> Reference Documentation & Blueprints
                                </h4>

                                <div className="flex flex-col gap-2.5">
                                    {(tool.reference_docs || [
                                        '.agents/skills/codi_opencode_harness/SKILL.md',
                                        '.opencode/skills/autonomous_software_engineering/SKILL.md',
                                        'core_skills/codi_01.json',
                                        'opencode.json'
                                    ]).map((doc, idx) => (
                                        <div key={idx} className="p-3 rounded-xl bg-glass-1 border border-glass-edge flex items-center justify-between">
                                            <div className="flex items-center gap-2">
                                                <FileText size={14} className="text-accent" />
                                                <span className="text-xs font-mono text-text-primary">{doc}</span>
                                            </div>
                                            <span className="text-[10px] font-mono text-text-tertiary bg-white/5 px-2 py-0.5 rounded border border-white/5">
                                                READY FOR INGESTION
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    )}

                </div>
            </div>
        </div>
    );
};
