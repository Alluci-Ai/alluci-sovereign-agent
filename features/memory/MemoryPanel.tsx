import React, { useState, useEffect, useCallback } from 'react';
import { useStore } from '../../store/useStore';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { Search, Trash2, FileText, Database, Info, Layers, Zap } from 'lucide-react';
import { HLSMStats } from '../../components/Memory/HLSMStats';
import { ConsolidationTrigger } from '../../components/Memory/ConsolidationTrigger';
import { sovereignService } from '../../sovereignService';

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const MemoryPanel: React.FC<{ onClose: () => void }> = ({ onClose }) => {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { accessToken } = useStore();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [memories, setMemories] = useState<any[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const [loading, setLoading] = useState(false);
    const [selectedTier, setSelectedTier] = useState<number | 'All'>('All');

    const fetchMemories = useCallback(async () => {
        setLoading(true);
        try {
            const data = await sovereignService.listMemories(50, 0, selectedTier);
            setMemories(data.entries || []);
        } catch (e) { 
            console.error("Failed to fetch memories", e); 
        } finally {
            setLoading(false);
        }
    }, [selectedTier]);

    useEffect(() => {
        fetchMemories();
        const handleMemoryDeleted = () => {
            fetchMemories();
        };
        window.addEventListener('hlsm_memory_deleted', handleMemoryDeleted);
        return () => window.removeEventListener('hlsm_memory_deleted', handleMemoryDeleted);
    }, [fetchMemories]);

    const handleSearch = async () => {
        if (!searchQuery.trim()) {
            fetchMemories();
            return;
        }
        setLoading(true);
        try {
            // Re-using the same search API which now routes to H-LSM
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const results = await (sovereignService as any)._fetch(`/memory/search?q=${encodeURIComponent(searchQuery)}`);
            // Format H-LSM retrieval results like the list entries for the UI
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            setMemories(results.map((r: any) => ({
                id: r.id,
                content: r.content,
                source: r.source,
                tier: r.tier || 1,
                retention_score: r.retention_score || 1.0,
                created_at: Date.now() / 1000,
                extra_metadata: r.extra_metadata,
                promoted_to_l2: r.promoted_to_l2
            })));
        } catch (e) {
            console.error("Search failed", e);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id: string) => {
        // Optimistic UI update: remove item immediately for single-click responsiveness
        setMemories(prev => prev.filter(m => m.id !== id));
        try {
            await sovereignService.deleteMemory(id);
        } catch (e: any) {
            console.error("Delete warning", e);
            // If entry was already deleted on backend (404 / Not Found), maintain UI deletion
            if (e?.message && (e.message.includes('404') || e.message.includes('Not Found') || e.message.includes('Already deleted'))) {
                return;
            }
            fetchMemories();
        }
    };

    const handlePin = async (id: string, isPinned: boolean) => {
        try {
            await sovereignService.pinMemory(id, !isPinned);
            setMemories(prev => prev.map(m => {
                if (m.id === id) {
                    const md = m.extra_metadata ? JSON.parse(m.extra_metadata) : {};
                    md.pinned = !isPinned;
                    return { ...m, extra_metadata: JSON.stringify(md) };
                }
                return m;
            }));
        } catch (e) { console.error("Pin failed", e); }
    };

    const handlePromote = async (id: string, targetTier?: number) => {
        try {
            await sovereignService.promoteMemory(id, targetTier);
            fetchMemories();
        } catch (e) { console.error("Promote failed", e); }
    };

    const handleDemote = async (id: string) => {
        try {
            await sovereignService.demoteMemory(id);
            fetchMemories();
        } catch (e) { console.error("Demote failed", e); }
    };

    const [actionMsg, setActionMsg] = useState<{ text: string; type: 'info' | 'success' | 'warning' } | null>(null);
    const [actionRunning, setActionRunning] = useState(false);

    const handleAudit = async () => {
        setActionRunning(true);
        try {
            const report = await sovereignService.auditMemory();
            const scorePct = ((report.health_score || 1.0) * 100).toFixed(1);
            const dups = report.duplicate_clusters?.length || 0;
            const wasted = report.wasted_bytes_total || 0;
            setActionMsg({
                text: `Audit Complete: Health ${scorePct}% | ${dups} duplicate clusters (${wasted} B wasted) | Retrieval Bias: ${report.retrieval_bias_risk || 'NONE'}`,
                type: report.health_score < 0.9 ? 'warning' : 'success'
            });
            setTimeout(() => setActionMsg(null), 8000);
        } catch (e) {
            setActionMsg({ text: "Audit failed to execute", type: 'warning' });
        } finally {
            setActionRunning(false);
        }
    };

    const handleDeduplicate = async () => {
        setActionRunning(true);
        try {
            const res = await sovereignService.deduplicateMemory(false);
            setActionMsg({
                text: `Deduplication complete: ${res.pruned_count || 0} duplicate entries pruned. Reclaimed ${res.reclaimed_bytes || 0} B.`,
                type: 'success'
            });
            fetchMemories();
            setTimeout(() => setActionMsg(null), 6000);
        } catch (e) {
            setActionMsg({ text: "Deduplication error", type: 'warning' });
        } finally {
            setActionRunning(false);
        }
    };

    const handlePurgeAll = async () => {
        if (!window.confirm("⚠️ Are you sure you want to PURGE ALL memories from L0, L1, L2, and L3 databases? This will clear all stored memories without deleting the database structures.")) {
            return;
        }
        setActionRunning(true);
        try {
            await sovereignService.purgeAllMemories();
            setActionMsg({
                text: "All L0, L1, L2, and L3 memory entries have been purged successfully.",
                type: 'success'
            });
            fetchMemories();
            setTimeout(() => setActionMsg(null), 6000);
        } catch (e) {
            setActionMsg({ text: "Purge failed", type: 'warning' });
        } finally {
            setActionRunning(false);
        }
    };

    return (
        <div className="flex flex-col h-full max-w-4xl mx-auto w-full space-y-6 overflow-hidden">
            {/* H-LSM Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <Layers size={20} className="text-emerald-500" />
                        <h3 className="text-2xl font-bold tracking-tight text-white">Hierarchical Long-Short Manifold</h3>
                    </div>
                    <p className="text-xs font-mono text-zinc-500 uppercase tracking-widest">
                        Tiered Cognitive Memory (L0: Working | L1: Episodic | L2: Semantic | L3: Graph)
                    </p>
                </div>
                
                {/* Header Action Buttons */}
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleAudit}
                        disabled={actionRunning}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono rounded-lg bg-zinc-900/80 hover:bg-zinc-800 text-zinc-300 border border-zinc-700/60 transition-all disabled:opacity-50"
                        title="Run Deep 4-Tier Memory Audit"
                    >
                        <Zap size={13} className="text-indigo-400" />
                        <span>Audit</span>
                    </button>
                    <button
                        onClick={handleDeduplicate}
                        disabled={actionRunning}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono rounded-lg bg-emerald-950/40 hover:bg-emerald-900/50 text-emerald-300 border border-emerald-800/50 transition-all disabled:opacity-50"
                        title="Deduplicate Bloat & Clean Graph"
                    >
                        <Layers size={13} className="text-emerald-400" />
                        <span>Deduplicate Bloat</span>
                    </button>
                    <button
                        onClick={handlePurgeAll}
                        disabled={actionRunning}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono rounded-lg bg-rose-950/40 hover:bg-rose-900/50 text-rose-300 border border-rose-800/50 transition-all disabled:opacity-50"
                        title="Purge All Memories from L0-L3"
                    >
                        <Trash2 size={13} className="text-rose-400" />
                        <span>Purge All</span>
                    </button>
                </div>
            </div>

            {/* Notification Banner */}
            {actionMsg && (
                <div className={`p-3 rounded-lg border text-xs font-mono flex items-center justify-between ${
                    actionMsg.type === 'success' ? 'bg-emerald-950/40 border-emerald-800 text-emerald-300' :
                    actionMsg.type === 'warning' ? 'bg-amber-950/40 border-amber-800 text-amber-300' :
                    'bg-zinc-900 border-zinc-700 text-zinc-300'
                }`}>
                    <span>{actionMsg.text}</span>
                    <button onClick={() => setActionMsg(null)} className="text-zinc-500 hover:text-white ml-2">✕</button>
                </div>
            )}

            {/* Stats Dashboard */}
            <div className="glass-card p-6 bg-zinc-950/40 border-zinc-800/50">
               <HLSMStats />
            </div>

            {/* Control Strip */}
            <div className="flex flex-col md:flex-row gap-4 items-center">
                <div className="relative flex-1 group w-full">
                    <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-zinc-600 group-focus-within:text-emerald-500 transition-colors" />
                    <input
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                        placeholder="Search manifold content..."
                        className="w-full bg-zinc-900/50 border border-zinc-800 rounded-xl py-3 pl-12 pr-4 text-sm text-white focus:outline-none focus:border-emerald-500/50 focus:bg-zinc-900/80 transition-all font-mono"
                    />
                </div>
                <div className="w-full md:w-auto">
                    <ConsolidationTrigger onComplete={fetchMemories} />
                </div>
            </div>

            {/* Tier Tabs */}
            <div className="flex space-x-2 p-1 bg-zinc-900/50 rounded-lg overflow-x-auto custom-scrollbar">
                {(['All', 0, 1, 2, 3] as const).map(tier => (
                    <button
                        key={tier}
                        onClick={() => setSelectedTier(tier)}
                        className={`px-4 py-1.5 text-xs font-mono rounded-md whitespace-nowrap transition-all ${selectedTier === tier ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50 border border-transparent'}`}
                    >
                        {tier === 'All' ? 'ALL TIERS' : tier === 0 ? 'WORKING (L0)' : tier === 1 ? 'EPISODIC (L1)' : tier === 2 ? 'SEMANTIC (L2)' : 'GRAPH (L3)'}
                    </button>
                ))}
            </div>

            {/* Memory Stream */}
            <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
                {memories.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-20 opacity-20 text-zinc-400">
                        <Database size={48} strokeWidth={1} className="mb-4" />
                        <p className="font-mono text-xs uppercase tracking-widest">Manifold Void — No active memories</p>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {memories.map((m) => (
                            <div key={m.id} className="group glass-card p-4 hover:border-emerald-900/40 transition-all bg-zinc-900/20 relative overflow-hidden">
                                {/* Tier Indicator */}
                                <div className={`absolute top-0 left-0 w-1 h-full ${
                                    m.tier === 0 ? 'bg-zinc-600' : 
                                    m.tier === 3 || m.promoted_to_l3 ? 'bg-purple-500' :
                                    m.tier === 2 || m.promoted_to_l2 ? 'bg-emerald-500' : 'bg-blue-500'
                                }`} />

                                <div className="flex justify-between items-start mb-2">
                                    <div className="flex items-center gap-3">
                                        <div className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-tighter ${
                                            m.tier === 0 ? 'bg-zinc-800 text-zinc-400' :
                                            m.tier === 3 || m.promoted_to_l3 ? 'bg-purple-900/30 text-purple-400' :
                                            m.tier === 2 || m.promoted_to_l2 ? 'bg-emerald-900/30 text-emerald-400' : 'bg-blue-900/30 text-blue-400'
                                        }`}>
                                            Tier {m.tier ?? 1} {m.tier === 0 ? 'Working' : (m.tier === 3 || m.promoted_to_l3) ? 'Graph' : (m.tier === 2 || m.promoted_to_l2) ? 'Semantic' : 'Episodic'}
                                        </div>
                                        <span className="text-[10px] text-zinc-600 font-mono">
                                            ID: {m.id.substring(0, 12)}...
                                        </span>
                                        {(() => {
                                            const isPinned = m.extra_metadata && m.extra_metadata.includes('"pinned": true');
                                            return isPinned ? (
                                                <span className="text-[10px] text-amber-500 font-bold bg-amber-500/10 px-1.5 rounded">PINNED</span>
                                            ) : null;
                                        })()}
                                    </div>
                                    <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button 
                                            onClick={() => handlePin(m.id, !!(m.extra_metadata && m.extra_metadata.includes('"pinned": true')))} 
                                            className="text-zinc-600 hover:text-amber-500 p-1 rounded hover:bg-white/5 transition-all text-xs"
                                            title="Toggle Pin"
                                        >
                                            Pin
                                        </button>
                                        {(m.tier === 1 && !m.promoted_to_l2 && !m.promoted_to_l3) && (
                                            <button 
                                                onClick={() => handlePromote(m.id, 2)} 
                                                className="text-zinc-600 hover:text-emerald-500 p-1 rounded hover:bg-white/5 transition-all text-xs"
                                                title="Promote to Semantic Memory (L2)"
                                            >
                                                Promote L2
                                            </button>
                                        )}
                                        {((m.tier === 2 || m.promoted_to_l2) && !m.promoted_to_l3) && (
                                            <button 
                                                onClick={() => handlePromote(m.id, 3)} 
                                                className="text-zinc-600 hover:text-purple-500 p-1 rounded hover:bg-white/5 transition-all text-xs"
                                                title="Promote to Graph Memory (L3)"
                                            >
                                                Promote L3
                                            </button>
                                        )}
                                        {(m.tier === 2 || m.tier === 3 || m.promoted_to_l2 || m.promoted_to_l3) && (
                                            <button 
                                                onClick={() => handleDemote(m.id)} 
                                                className="text-zinc-600 hover:text-orange-500 p-1 rounded hover:bg-white/5 transition-all text-xs"
                                                title="Demote to lower tier"
                                            >
                                                Demote
                                            </button>
                                        )}
                                        <button 
                                            onClick={() => handleDelete(m.id)} 
                                            className="text-zinc-600 hover:text-red-500 transition-colors p-1"
                                        >
                                            <Trash2 size={14} />
                                        </button>
                                    </div>
                                </div>

                                <p className="text-sm leading-relaxed text-zinc-300 mb-3 pl-2">
                                    {m.content}
                                </p>

                                <div className="flex items-center gap-4 text-[10px] font-mono text-zinc-600 px-2 mt-2">
                                    <div className="flex items-center gap-1">
                                        <Zap size={10} className="text-yellow-600" />
                                        <span>RETENTION: {(m.retention_score * 100).toFixed(1)}%</span>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <Info size={10} />
                                        <span>SOURCE: {m.source || 'TRANSCRIPT'}</span>
                                    </div>
                                    {m.created_at && (
                                        <div className="ml-auto opacity-50">
                                            {new Date(m.created_at * 1000).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};
