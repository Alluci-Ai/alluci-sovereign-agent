import React, { useState, useEffect, useCallback } from 'react';
import { ShieldCheck, AlertTriangle, RefreshCw, Trash2, CheckCircle2, Database, Layers, Eye } from 'lucide-react';
import { sovereignService } from '../../sovereignService';

interface DuplicateCluster {
    cluster_id: string;
    cluster_type: string;
    canonical_id: string;
    duplicate_ids: string[];
    entity_title: string;
    entity_preview: string;
    affected_tiers: string[];
    wasted_bytes: number;
    confidence: number;
}

interface HealthReport {
    health_score: number;
    total_records: { l0: number; l1: number; l2: number; l3: number; total: number };
    duplicate_clusters: DuplicateCluster[];
    orphan_counts: { dangling_keypoints: number; orphaned_l3_memories: number };
    wasted_bytes_total: number;
    retrieval_bias_risk: string;
    audit_timestamp: number;
}

export const MemoryHealthDashboard: React.FC<{ onMemoryUpdated?: () => void }> = ({ onMemoryUpdated }) => {
    const [report, setReport] = useState<HealthReport | null>(null);
    const [loading, setLoading] = useState(false);
    const [actionLoading, setActionLoading] = useState(false);
    const [actionResult, setActionResult] = useState<any | null>(null);
    const [selectedCluster, setSelectedCluster] = useState<DuplicateCluster | null>(null);

    const runAudit = useCallback(async () => {
        setLoading(true);
        try {
            const data = await sovereignService.auditMemory();
            setReport(data);
        } catch (err) {
            console.error("Failed to fetch memory audit", err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        runAudit();
    }, [runAudit]);

    const handleDeduplicate = async (dryRun: boolean) => {
        setActionLoading(true);
        try {
            const res = await sovereignService.deduplicateMemory(dryRun);
            setActionResult(res);
            if (!dryRun) {
                await runAudit();
                onMemoryUpdated?.();
            }
        } catch (err) {
            console.error("Deduplication error", err);
        } finally {
            setActionLoading(false);
        }
    };

    const formatBytes = (bytes: number) => {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const getScoreColor = (score: number) => {
        if (score >= 0.9) return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10';
        if (score >= 0.7) return 'text-amber-400 border-amber-500/30 bg-amber-500/10';
        return 'text-rose-400 border-rose-500/30 bg-rose-500/10';
    };

    const getBiasBadge = (risk: string) => {
        switch (risk) {
            case 'NONE':
                return <span className="px-2 py-0.5 text-xs font-mono rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Bias: None (Balanced RRF)</span>;
            case 'LOW':
                return <span className="px-2 py-0.5 text-xs font-mono rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">Bias: Low</span>;
            case 'MEDIUM':
                return <span className="px-2 py-0.5 text-xs font-mono rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">Bias: Medium (Skew Warning)</span>;
            default:
                return <span className="px-2 py-0.5 text-xs font-mono rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">Bias: High (Retrieval Skewed)</span>;
        }
    };

    return (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-2xl backdrop-blur-md mb-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
                <div className="flex items-center space-x-3">
                    <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
                        <ShieldCheck className="w-5 h-5" />
                    </div>
                    <div>
                        <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
                            4-Tier H-LSM Deep Memory Auditor & CAS Deduplicator
                        </h2>
                        <p className="text-xs text-slate-400">
                            Continuous structural & cryptographic audit of L0 (RAM), L1 (SQLite), L2 (Vectors), and L3 (KùzuDB Graph).
                        </p>
                    </div>
                </div>

                <div className="flex items-center space-x-2">
                    <button
                        onClick={runAudit}
                        disabled={loading}
                        className="px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 flex items-center gap-1.5 transition-all disabled:opacity-50"
                    >
                        <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                        {loading ? 'Auditing...' : 'Run Deep Audit'}
                    </button>
                    <button
                        onClick={() => handleDeduplicate(false)}
                        disabled={actionLoading || !report || report.duplicate_clusters.length === 0}
                        className="px-3 py-1.5 text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg border border-emerald-500/50 flex items-center gap-1.5 shadow-lg shadow-emerald-900/20 transition-all disabled:opacity-50"
                    >
                        <Trash2 className="w-3.5 h-3.5" />
                        {actionLoading ? 'Cleaning...' : 'Deduplicate & Purge Bloat'}
                    </button>
                </div>
            </div>

            {report && (
                <div className="space-y-4">
                    {/* Top Metric Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                        <div className={`p-3 rounded-lg border flex items-center justify-between ${getScoreColor(report.health_score)}`}>
                            <div>
                                <span className="text-xs uppercase tracking-wider font-mono opacity-80">Health Score</span>
                                <div className="text-2xl font-bold font-mono">
                                    {(report.health_score * 100).toFixed(1)}%
                                </div>
                            </div>
                            <CheckCircle2 className="w-8 h-8 opacity-70" />
                        </div>

                        <div className="p-3 rounded-lg border border-slate-800 bg-slate-950/50 flex flex-col justify-between">
                            <span className="text-xs uppercase tracking-wider font-mono text-slate-400">Total Records</span>
                            <div className="text-xl font-bold font-mono text-slate-200">
                                {report.total_records.total}
                            </div>
                            <span className="text-[11px] text-slate-500 font-mono">
                                L0: {report.total_records.l0} | L1: {report.total_records.l1} | L3: {report.total_records.l3}
                            </span>
                        </div>

                        <div className="p-3 rounded-lg border border-slate-800 bg-slate-950/50 flex flex-col justify-between">
                            <span className="text-xs uppercase tracking-wider font-mono text-slate-400">Duplicate Clusters</span>
                            <div className="text-xl font-bold font-mono text-amber-400">
                                {report.duplicate_clusters.length}
                            </div>
                            <span className="text-[11px] text-slate-500 font-mono">
                                Wasted: {formatBytes(report.wasted_bytes_total)}
                            </span>
                        </div>

                        <div className="p-3 rounded-lg border border-slate-800 bg-slate-950/50 flex flex-col justify-between">
                            <span className="text-xs uppercase tracking-wider font-mono text-slate-400">Retrieval Integrity</span>
                            <div className="mt-1">
                                {getBiasBadge(report.retrieval_bias_risk)}
                            </div>
                            <span className="text-[11px] text-slate-500 font-mono">
                                Dangling Nodes: {report.orphan_counts.dangling_keypoints + report.orphan_counts.orphaned_l3_memories}
                            </span>
                        </div>
                    </div>

                    {/* Action Execution Feedback */}
                    {actionResult && (
                        <div className="p-3.5 rounded-lg bg-emerald-950/30 border border-emerald-500/30 text-xs text-emerald-200 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                                <span>
                                    {actionResult.message} 
                                    {actionResult.deleted_records && ` (Pruned ${actionResult.deleted_records.total} duplicate entities, freed ${formatBytes(actionResult.freed_bytes_total)})`}
                                </span>
                            </div>
                            <button
                                onClick={() => setActionResult(null)}
                                className="text-emerald-400 hover:text-emerald-200 font-mono text-xs underline"
                            >
                                Dismiss
                            </button>
                        </div>
                    )}

                    {/* Duplicate Cluster Inspector */}
                    <div>
                        <h3 className="text-xs font-mono uppercase text-slate-400 mb-2 flex items-center gap-1.5">
                            <Layers className="w-3.5 h-3.5 text-indigo-400" />
                            Detected Duplicate Clusters & Orphan Topologies ({report.duplicate_clusters.length})
                        </h3>

                        {report.duplicate_clusters.length === 0 ? (
                            <div className="p-4 rounded-lg bg-slate-950/40 border border-slate-800/80 text-center text-xs text-slate-500 font-mono flex items-center justify-center gap-2">
                                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                                No duplicate memories or orphaned graph nodes detected. Single source of truth active.
                            </div>
                        ) : (
                            <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                                {report.duplicate_clusters.map((cluster) => (
                                    <div
                                        key={cluster.cluster_id}
                                        className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition-all text-xs flex items-center justify-between"
                                    >
                                        <div className="space-y-1 max-w-[70%]">
                                            <div className="flex items-center gap-2">
                                                <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                                    {cluster.cluster_type.replace('_', ' ')}
                                                </span>
                                                <span className="font-medium text-slate-200 truncate">
                                                    {cluster.entity_title}
                                                </span>
                                            </div>
                                            <p className="text-slate-400 text-[11px] truncate font-mono">
                                                {cluster.entity_preview}
                                            </p>
                                            <div className="flex items-center gap-3 text-[10px] text-slate-500 font-mono">
                                                <span>Master: <strong className="text-emerald-400">{cluster.canonical_id}</strong></span>
                                                <span>Duplicates: <strong className="text-rose-400">{cluster.duplicate_ids.length}</strong></span>
                                                <span>Tiers: {cluster.affected_tiers.join(', ')}</span>
                                                <span>Wasted: {formatBytes(cluster.wasted_bytes)}</span>
                                            </div>
                                        </div>

                                        <button
                                            onClick={() => setSelectedCluster(cluster)}
                                            className="px-2.5 py-1 text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 flex items-center gap-1"
                                        >
                                            <Eye className="w-3 h-3" />
                                            Inspect
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Cluster Detail Modal */}
            {selectedCluster && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
                    <div className="bg-slate-900 border border-slate-700 rounded-xl p-5 max-w-lg w-full shadow-2xl space-y-4">
                        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                            <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
                                <AlertTriangle className="w-4 h-4 text-amber-400" />
                                Duplicate Cluster Breakdown
                            </h3>
                            <button
                                onClick={() => setSelectedCluster(null)}
                                className="text-slate-400 hover:text-slate-200 text-sm font-mono"
                            >
                                ✕
                            </button>
                        </div>

                        <div className="space-y-2 text-xs font-mono">
                            <div>
                                <span className="text-slate-500">Cluster ID:</span> {selectedCluster.cluster_id}
                            </div>
                            <div>
                                <span className="text-slate-500">Canonical Master ID:</span>{' '}
                                <span className="text-emerald-400 font-bold">{selectedCluster.canonical_id}</span>
                            </div>
                            <div>
                                <span className="text-slate-500">Duplicate Node IDs to Prune:</span>
                                <ul className="mt-1 space-y-1 text-rose-400 max-h-32 overflow-y-auto pl-2 border-l border-rose-500/30">
                                    {selectedCluster.duplicate_ids.map(id => (
                                        <li key={id}>• {id}</li>
                                    ))}
                                </ul>
                            </div>
                            <div className="pt-2 border-t border-slate-800">
                                <span className="text-slate-500">Entity Preview:</span>
                                <p className="mt-1 p-2 rounded bg-slate-950 text-slate-300 text-[11px] leading-relaxed">
                                    {selectedCluster.entity_preview}
                                </p>
                            </div>
                        </div>

                        <div className="flex justify-end pt-2">
                            <button
                                onClick={() => setSelectedCluster(null)}
                                className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-200 rounded border border-slate-700"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
