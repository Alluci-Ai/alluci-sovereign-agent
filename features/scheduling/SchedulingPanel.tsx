import React, { useEffect, useState } from 'react';
import { useStore } from '../../store/useStore';
import { Calendar, Play, Pause, Clock, AlertCircle, Plus, ChevronDown, ChevronUp } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

interface CronJob {
    id: string;
    name: string;
    schedule_type: string;
    expression: string;
    enabled: boolean;
    next_run?: string;
    last_run?: string;
    status: string;
}

interface CronRun {
    id: string;
    job_id: string;
    started_at: string;
    finished_at?: string;
    status: string;
    output?: string;
}

/**
 * SchedulingPanel — Cron engine management with job list,
 * status indicators, and run history.
 */
export const SchedulingPanel: React.FC = () => {
    const { accessToken } = useStore();
    const [jobs, setJobs] = useState<CronJob[]>([]);
    const [runs, setRuns] = useState<CronRun[]>([]);
    const [expandedJob, setExpandedJob] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    const headers = accessToken ? { Authorization: `Bearer ${accessToken}` } : {};

    const fetchJobs = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${DAEMON_URL}/api/cron/jobs`, { credentials: 'include', headers });
            if (res.ok) setJobs(await res.json());
        } catch (err) {
            console.error('[SchedulingPanel] Fetch error:', err);
        } finally {
            setLoading(false);
        }
    };

    const fetchRuns = async (jobId: string) => {
        try {
            const res = await fetch(`${DAEMON_URL}/api/cron/runs?job_id=${jobId}`, { credentials: 'include', headers });
            if (res.ok) setRuns(await res.json());
        } catch (err) {
            console.error('[SchedulingPanel] Runs fetch error:', err);
        }
    };

    useEffect(() => { fetchJobs(); }, []);

    const toggleJob = (jobId: string) => {
        if (expandedJob === jobId) {
            setExpandedJob(null);
        } else {
            setExpandedJob(jobId);
            fetchRuns(jobId);
        }
    };

    const activeCount = jobs.filter(j => j.enabled).length;

    return (
        <div className="inline-panel-wrapper">
            <div className="inline-panel">
                <div className="inline-panel__header">
                    <h2 className="inline-panel__title">
                        <Calendar size={16} className="mr-2 inline" />
                        Scheduling
                    </h2>
                    <div className="glass-btn" style={{ fontSize: 10, cursor: 'default' }}>
                        {activeCount} active / {jobs.length} total
                    </div>
                </div>

                <div className="inline-panel__body">
                    {loading ? (
                        <div className="inline-panel__empty"><p>Loading cron jobs…</p></div>
                    ) : jobs.length === 0 ? (
                        <div className="inline-panel__empty">
                            <p>No scheduled jobs yet.</p>
                            <p className="text-xs opacity-50">Create a cron job to automate agent tasks.</p>
                        </div>
                    ) : (
                        <div className="cron-job-list">
                            {jobs.map(job => (
                                <div key={job.id} className="cron-job-card">
                                    <div className="cron-job-card__header" onClick={() => toggleJob(job.id)}>
                                        <div className="cron-job-card__status">
                                            {job.enabled
                                                ? <Play size={13} className="text-accent" />
                                                : <Pause size={13} className="opacity-40" />}
                                        </div>
                                        <div className="cron-job-card__info">
                                            <div className="cron-job-card__name">{job.name}</div>
                                            <div className="cron-job-card__schedule">
                                                <span className="cron-job-card__type">{job.schedule_type}</span>
                                                <code>{job.expression}</code>
                                            </div>
                                        </div>
                                        <div className="cron-job-card__meta">
                                            {job.next_run && (
                                                <div className="cron-job-card__next">
                                                    <Clock size={10} /> Next: {new Date(job.next_run).toLocaleString()}
                                                </div>
                                            )}
                                        </div>
                                        {expandedJob === job.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                    </div>

                                    {expandedJob === job.id && (
                                        <div className="cron-job-card__runs">
                                            <div className="cron-job-card__runs-title">Run History</div>
                                            {runs.length === 0 ? (
                                                <div className="text-[11px] opacity-40 py-4 text-center">No runs yet</div>
                                            ) : runs.map(run => (
                                                <div key={run.id} className="cron-run-entry">
                                                    <span className={`cron-run-entry__status ${run.status === 'success' ? 'cron-run-entry__status--ok' : 'cron-run-entry__status--fail'}`}>
                                                        {run.status}
                                                    </span>
                                                    <span className="cron-run-entry__time">{new Date(run.started_at).toLocaleString()}</span>
                                                    {run.output && <div className="cron-run-entry__output">{run.output.slice(0, 200)}</div>}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SchedulingPanel;
