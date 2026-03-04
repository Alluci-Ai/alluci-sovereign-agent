import React, { useState, useEffect, useCallback } from 'react';
import { useStore } from '../../store/useStore';
import { CheckCircle2, XCircle, Clock, Search, ExternalLink } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

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
            const res = await fetch(`${DAEMON_URL}/api/cron/runs?limit=30`, {
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
        if (!end) return 'Running...';
        const ms = new Date(end).getTime() - new Date(start).getTime();
        return `${(ms / 1000).toFixed(1)}s`;
    };

    if (loading) return (
        <div className="h-full flex items-center justify-center opacity-50 animate-pulse text-xs font-mono tracking-widest">
            LOADING_TRACE_HISTORY...
        </div>
    );

    if (runs.length === 0) return (
        <div className="h-full flex flex-col items-center justify-center opacity-40 text-center gap-3">
            <Search size={32} />
            <span className="text-xs font-mono tracking-widest">NO_EXECUTIONS_LOGGED</span>
        </div>
    );

    return (
        <div className="flex flex-col gap-2">
            {runs.map((run) => (
                <div key={run.id} className="bg-glass-1 border border-glass-edge rounded-lg overflow-hidden animate-in fade-in flex flex-col transition-all">

                    <button
                        onClick={() => setExpandedId(expandedId === run.id ? null : run.id)}
                        className={`flex items-center justify-between p-3 text-left transition-colors hover:bg-white/5 ${expandedId === run.id ? 'bg-glass-2 border-b border-glass-edge' : ''}`}
                    >
                        <div className="flex items-center gap-3 min-w-0">
                            {run.status === 'ok' ? (
                                <CheckCircle2 size={14} className="text-status-good flex-shrink-0" />
                            ) : (
                                <XCircle size={14} className="text-status-error flex-shrink-0" />
                            )}
                            <div className="flex flex-col min-w-0">
                                <span className="text-xs font-medium text-text-primary capitalize truncate">Job #{run.job_id} Exection</span>
                                <span className="text-[10px] font-mono text-text-tertiary">
                                    {new Date(run.started_at).toLocaleString()}
                                </span>
                            </div>
                        </div>

                        <div className="flex items-center gap-4 text-[10px] font-mono opacity-80 shrink-0">
                            <span className="flex items-center gap-1.5"><Clock size={10} className="text-accent" /> {formatDuration(run.started_at, run.finished_at)}</span>
                            <span className={`px-1.5 py-0.5 rounded border ${run.delivery_status !== 'none' && run.delivery_status !== 'delivered' ? 'text-status-warning border-status-warning/20 bg-status-warning/10' : 'border-white/10 text-text-tertiary bg-white/5'}`}>
                                {run.delivery_status.substring(0, 10).toUpperCase()}
                            </span>
                        </div>
                    </button>

                    {expandedId === run.id && (
                        <div className="p-3 bg-glass-pressed border-t border-glass-edge text-[11px] font-mono text-text-secondary whitespace-pre-wrap max-h-48 overflow-y-auto custom-scrollbar relative">
                            {run.log_text || 'No output captured.'}
                            {run.log_text.length > 50 && (
                                <button
                                    className="absolute top-2 right-2 p-1 bg-glass-1 border border-glass-edge rounded opacity-50 hover:opacity-100"
                                    onClick={(e) => { e.stopPropagation(); navigator.clipboard.writeText(run.log_text); }}
                                    title="Copy raw log"
                                >
                                    <ExternalLink size={12} />
                                </button>
                            )}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
};

export default CronRunHistory;
