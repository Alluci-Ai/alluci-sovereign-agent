import React, { useState, useEffect, useCallback } from 'react';
import { useStore } from '../../store/useStore';
import { Clock, Play, Pause, Settings, Plus, CalendarDays, History, Trash2, Copy, Rocket } from 'lucide-react';
import CronJobForm from './CronJobForm';
import CronRunHistory from './CronRunHistory';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

export interface CronJob {
    id: number;
    name: string;
    schedule_type: 'interval' | 'cron' | 'run_at';
    schedule_value: string;
    payload: string;
    model_override?: string;
    thinking_level?: string;
    delivery_channel?: string;
    delivery_account?: string;
    delivery_to?: string;
    delivery_mode?: string;
    reset_context: boolean;
    enabled: boolean;
    created_at?: string;
    last_run_at?: string;
}

export const CronPanel: React.FC = () => {
    const { accessToken } = useStore();
    const [jobs, setJobs] = useState<CronJob[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'jobs' | 'history'>('jobs');
    const [editingJob, setEditingJob] = useState<CronJob | Partial<CronJob> | null>(null);

    const fetchJobs = useCallback(async () => {
        try {
            const res = await fetch(`${DAEMON_URL}/api/cron/jobs`, {
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            });
            if (res.ok) setJobs(await res.json());
        } catch (err) {
            console.error('Failed to fetch cron jobs', err);
        } finally {
            setLoading(false);
        }
    }, [accessToken]);

    useEffect(() => {
        fetchJobs();
    }, [fetchJobs]);

    const toggleEnable = async (job: CronJob) => {
        try {
            await fetch(`${DAEMON_URL}/api/cron/jobs/${job.id}`, {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: !job.enabled }),
                credentials: 'include'
            });
            fetchJobs();
        } catch (err) { }
    };

    const forceRun = async (id: number) => {
        try {
            await fetch(`${DAEMON_URL}/api/cron/jobs/${id}/run`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            });
            alert('Job dispatched to task queue.');
            fetchJobs();
        } catch (err) { }
    };

    const cloneJob = async (id: number) => {
        try {
            await fetch(`${DAEMON_URL}/api/cron/jobs/${id}/clone`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            });
            fetchJobs();
        } catch (err) { }
    };

    const deleteJob = async (id: number) => {
        if (!confirm('Delete this scheduled job?')) return;
        try {
            await fetch(`${DAEMON_URL}/api/cron/jobs/${id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            });
            fetchJobs();
        } catch (err) { }
    };

    if (editingJob) {
        return <CronJobForm job={editingJob} onSave={() => { setEditingJob(null); fetchJobs(); }} onCancel={() => setEditingJob(null)} />;
    }

    return (
        <div className="flex flex-col h-full animate-in fade-in duration-300">
            {/* Header */}
            <div className="flex-shrink-0 p-4 pb-0">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-sm font-semibold tracking-tight flex items-center gap-2">
                        <Clock className="text-accent" size={16} /> Crons & Scheduled Jobs
                    </h2>
                    <button
                        onClick={() => setEditingJob({ schedule_type: 'interval', enabled: true, delivery_mode: 'none', reset_context: false })}
                        className="glass-btn glass-btn--primary px-3 py-1.5 flex items-center gap-2 text-xs"
                    >
                        <Plus size={14} /> New Job
                    </button>
                </div>

                <p className="text-[11px] text-text-tertiary mb-4 leading-relaxed tracking-wide">
                    Crons are deterministic time-based alarm clocks. When a cron executes, it automatically dispatches a new independent Task into the event queue for resolution.
                </p>

                <div className="flex gap-1 bg-glass-pressed p-1 rounded-lg w-max mb-4">
                    <button
                        onClick={() => setActiveTab('jobs')}
                        className={`px-3 py-1.5 rounded-md text-[11px] font-medium transition-all ${activeTab === 'jobs' ? 'bg-glass-1 text-accent shadow-sm' : 'text-text-tertiary hover:text-text-secondary'}`}
                    >
                        Active Jobs ({jobs.length})
                    </button>
                    <button
                        onClick={() => setActiveTab('history')}
                        className={`px-3 py-1.5 rounded-md text-[11px] font-medium transition-all ${activeTab === 'history' ? 'bg-glass-1 text-accent shadow-sm' : 'text-text-tertiary hover:text-text-secondary'}`}
                    >
                        Run History
                    </button>
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-1 overflow-y-auto px-4 pb-4 custom-scrollbar">
                {loading ? (
                    <div className="h-full flex items-center justify-center opacity-50 animate-pulse text-xs font-mono tracking-widest">
                        LOADING_CRONS...
                    </div>
                ) : activeTab === 'history' ? (
                    <CronRunHistory />
                ) : jobs.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center opacity-40 text-center gap-3">
                        <CalendarDays size={32} />
                        <span className="text-xs font-mono tracking-widest">NO_JOBS_CONFIGURED</span>
                    </div>
                ) : (
                    <div className="flex flex-col gap-3">
                        {jobs.map(job => (
                            <div key={job.id} className={`bg-glass-1 border ${job.enabled ? 'border-accent/30' : 'border-glass-edge opacity-60'} rounded-xl p-4 flex flex-col transition-all hover:border-accent/40`}>
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex flex-col">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="font-medium text-sm text-text-primary">{job.name}</span>
                                            <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${job.enabled ? 'bg-status-good/10 text-status-good border-status-good/20' : 'bg-glass-2 text-text-tertiary border-glass-edge'}`}>
                                                {job.enabled ? 'ACTIVE' : 'PAUSED'}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-2 text-[10px] font-mono text-text-secondary">
                                            <Clock size={10} className="text-accent opacity-70" />
                                            <span className="bg-glass-pressed px-1.5 rounded">
                                                {job.schedule_type}: {job.schedule_value}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="flex gap-1">
                                        <button onClick={() => toggleEnable(job)} className="p-1.5 glass-btn text-text-tertiary hover:text-text-primary" title={job.enabled ? "Pause" : "Resume"}>
                                            {job.enabled ? <Pause size={14} /> : <Play size={14} />}
                                        </button>
                                        <button onClick={() => forceRun(job.id)} className="p-1.5 glass-btn text-text-tertiary hover:text-accent" title="Force Run Now">
                                            <Rocket size={14} />
                                        </button>
                                        <button onClick={() => setEditingJob(job)} className="p-1.5 glass-btn text-text-tertiary hover:text-text-primary" title="Edit">
                                            <Settings size={14} />
                                        </button>
                                        <button onClick={() => cloneJob(job.id)} className="p-1.5 glass-btn text-text-tertiary hover:text-text-primary" title="Clone">
                                            <Copy size={14} />
                                        </button>
                                        <button onClick={() => deleteJob(job.id)} className="p-1.5 glass-btn text-status-error/70 hover:text-status-error" title="Delete">
                                            <Trash2 size={14} />
                                        </button>
                                    </div>
                                </div>
                                <div className="text-[11px] text-text-tertiary bg-glass-pressed rounded-lg p-2 font-mono whitespace-pre-wrap truncate">
                                    {job.payload.length > 100 ? job.payload.substring(0, 100) + '...' : job.payload}
                                </div>
                                <div className="mt-3 flex justify-between items-center text-[10px] text-text-tertiary border-t border-glass-edge pt-2">
                                    <span>Created: {new Date(job.created_at || '').toLocaleDateString()}</span>
                                    {job.last_run_at ? (
                                        <span className="text-text-secondary">Last: {new Date(job.last_run_at).toLocaleString()}</span>
                                    ) : (
                                        <span>Never run</span>
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

export default CronPanel;
