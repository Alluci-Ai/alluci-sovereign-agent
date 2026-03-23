import React, { useState, useEffect, useCallback } from 'react';
import { useStore } from '../../store/useStore';
import { Search, Trash2, FileText, Database, Info, Layers, Zap } from 'lucide-react';
import { HLSMStats } from '../../components/Memory/HLSMStats';
import { ConsolidationTrigger } from '../../components/Memory/ConsolidationTrigger';
import { sovereignService } from '../../sovereignService';

export const MemoryPanel: React.FC<{ onClose: () => void }> = ({ onClose }) => {
    const { accessToken } = useStore();
    const [memories, setMemories] = useState<any[]>([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [loading, setLoading] = useState(false);

    const fetchMemories = useCallback(async () => {
        setLoading(true);
        try {
            const data = await sovereignService.listMemories(50, 0);
            setMemories(data.entries || []);
        } catch (e) { 
            console.error("Failed to fetch memories", e); 
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchMemories();
    }, [fetchMemories]);

    const handleSearch = async () => {
        if (!searchQuery.trim()) {
            fetchMemories();
            return;
        }
        setLoading(true);
        try {
            // Re-using the same search API which now routes to H-LSM
            const results = await (sovereignService as any)._fetch(`/memory/search?q=${encodeURIComponent(searchQuery)}`);
            // Format H-LSM retrieval results like the list entries for the UI
            setMemories(results.map((r: any) => ({
                id: r.id,
                content: r.content,
                source: r.source,
                tier: r.tier || 1,
                retention_score: r.retention_score || 1.0,
                created_at: Date.now() / 1000
            })));
        } catch (e) {
            console.error("Search failed", e);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id: string) => {
        try {
            const res = await sovereignService.deleteMemory(id);
            if (res.status === "SUCCESS") {
                setMemories(prev => prev.filter(m => m.id !== id));
            }
        } catch (e) {
            console.error("Delete failed", e);
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
                        Tiered Cognitive Memory (L0: Working | L1: Episodic | L2: Semantic)
                    </p>
                </div>
            </div>

            {/* Stats Dashboard */}
            <div className="glass-card p-6 bg-zinc-950/40 border-zinc-800/50">
               <HLSMStats />
            </div>

            {/* Control Strip */}
            <div className="flex flex-col md:flex-row gap-4 items-center">
                <div className="relative flex-1 group">
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
                                    m.tier === 2 ? 'bg-emerald-500' : 'bg-blue-500'
                                }`} />

                                <div className="flex justify-between items-start mb-2">
                                    <div className="flex items-center gap-3">
                                        <div className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-tighter ${
                                            m.tier === 0 ? 'bg-zinc-800 text-zinc-400' :
                                            m.tier === 2 ? 'bg-emerald-900/30 text-emerald-400' : 'bg-blue-900/30 text-blue-400'
                                        }`}>
                                            Tier {m.tier ?? 1} {m.tier === 0 ? 'Working' : m.tier === 2 ? 'Semantic' : 'Episodic'}
                                        </div>
                                        <span className="text-[10px] text-zinc-600 font-mono">
                                            ID: {m.id.substring(0, 12)}...
                                        </span>
                                    </div>
                                    <button 
                                        onClick={() => handleDelete(m.id)} 
                                        className="text-zinc-600 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100 p-1"
                                    >
                                        <Trash2 size={14} />
                                    </button>
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
