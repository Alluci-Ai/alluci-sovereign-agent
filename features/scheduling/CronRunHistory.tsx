import React, { useState, useEffect, useCallback } from 'react';
import { useStore } from '../../store/useStore';
import { CheckCircle2, XCircle, Clock, Search, ExternalLink, Hash, Activity } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://127.0.0.1:8000';

interface CronRun {
    id: number;
    job_id: number;
    started_at: string;
    finished_at?: string;
    status: string;
    delivery_status: string;
    log_text: string;
}

export const CronRunHistory: React.FC = () => {
    const { accessToken } = useStore();
    const [runs, setRuns] = useState<CronRun[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedId, setExpandedId] = useState<number | null>(null);

    const fetchRuns = useCallback(async () => {
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/cron/runs?limit=30`, {
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            });
            if (res.ok) setRuns(await res.json());
        } catch (err) {
            console.error('Failed to fetch cron runs', err);
        } finally {
            setLoading(false);
        }
    }, [accessToken]);

    useEffect(() => {
        fetchRuns();
    }, [fetchRuns]);

    const formatDuration = (start: string, end?: string) => {
        if (!end) return 'Active';
        const ms = new Date(end).getTime() - new Date(start).getTime();
        if (ms < 1000) return `${ms}ms`;
        return `${(ms / 1000).toFixed(1)}s`;
    };

    if (loading) return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200 }} className="opacity-40 font-mono text-xs tracking-widest animate-pulse">
            RETRIEVING_EXECUTION_LOGS...
        </div>
    );

    if (runs.length === 0) return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: 300, gap: 16 }} className="opacity-30">
            <Search size={40} />
            <span className="text-sm font-medium">No execution history found in the manifold.</span>
        </div>
    );

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {runs.map((run) => (
                <div key={run.id} style={{
                    background: 'var(--glass-bg)',
                    border: '1px solid var(--glass-edge)',
                    borderRadius: 14, overflow: 'hidden',
                    boxShadow: 'var(--glass-shadow-sm)',
                    transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
                }}>
                    <button
                        onClick={() => setExpandedId(expandedId === run.id ? null : run.id)}
                        style={{
                            width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                            padding: '12px 16px', border: 'none', background: 'transparent', cursor: 'pointer',
                            textAlign: 'left'
                        }}
                        className="hover:bg-glass-bg-hover transition-colors"
                    >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                            <div style={{
                                width: 32, height: 32, borderRadius: 10,
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                background: run.status === 'ok' ? 'var(--status-good-tint)' : 'var(--status-error-tint)',
                                color: run.status === 'ok' ? 'var(--status-good)' : 'var(--status-error)'
                            }}>
                                {run.status === 'ok' ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                    <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>Trace #{run.id}</span>
                                    <span style={{ fontSize: 10, color: 'var(--text-tertiary)', fontWeight: 500 }} className="flex items-center gap-1">
                                        <Hash size={10} /> Job {run.job_id}
                                    </span>
                                </div>
                                <span style={{ fontSize: 10, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                                    {new Date(run.started_at).toLocaleString()}
                                </span>
                            </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2 }}>
                                <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.02em', display: 'flex', alignItems: 'center', gap: 4 }}>
                                    <Activity size={10} /> {formatDuration(run.started_at, run.finished_at)}
                                </span>
                                <span style={{
                                    fontSize: 9, fontWeight: 700, padding: '1px 6px', borderRadius: 4,
                                    background: run.delivery_status === 'delivered' ? 'var(--status-good-tint)' : 'var(--fill-quaternary)',
                                    color: run.delivery_status === 'delivered' ? 'var(--status-good)' : 'var(--text-tertiary)',
                                    border: '1px solid var(--separator)'
                                }}>
                                    {run.delivery_status.toUpperCase()}
                                </span>
                            </div>
                        </div>
                    </button>

                    {expandedId === run.id && (
                        <div style={{
                            padding: 16, background: 'var(--fill-quaternary)',
                            borderTop: '1px solid var(--separator)', position: 'relative'
                        }}>
                            <div style={{
                                fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)',
                                whiteSpace: 'pre-wrap', maxHeight: 300, overflowY: 'auto',
                                lineHeight: 1.6, paddingBottom: 8
                            }} className="scrollbar-hide">
                                {run.log_text || '// NO_LOG_DATA_RECORDED'}
                            </div>
                            <button
                                style={{
                                    position: 'absolute', top: 12, right: 12,
                                    padding: '6px 10px', background: 'var(--glass-bg)',
                                    border: '1px solid var(--glass-edge)', borderRadius: 8,
                                    fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)',
                                    display: 'flex', alignItems: 'center', gap: 6
                                }}
                                onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(run.log_text); }}
                                className="hover:bg-glass-bg-hover hover:text-text-primary transition-all"
                            >
                                <ExternalLink size={12} /> COPY_RAW
                            </button>
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
};

export default CronRunHistory;
