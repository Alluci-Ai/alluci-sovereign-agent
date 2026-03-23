import React, { useState, useEffect, useCallback } from 'react';
import { useStore } from '../../store/useStore';
import {
    Clock, Play, Pause, Settings, Plus, CalendarDays,
    History, Trash2, Copy, Rocket, ChevronDown, Filter,
    Search, AlertCircle
} from 'lucide-react';
import { CronJobForm } from './CronJobForm';
import { CronRunHistory } from './CronRunHistory';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://127.0.0.1:8000';

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
    const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'paused'>('all');
    const [typeFilter, setTypeFilter] = useState<string>('ALL');
    const [searchTerm, setSearchTerm] = useState('');
    const [showHistory, setShowHistory] = useState(false);
    const [editingJob, setEditingJob] = useState<CronJob | Partial<CronJob> | null>(null);
    const [showToast, setShowToast] = useState<string | null>(null);

    // Quick-add state
    const [newName, setNewName] = useState('');
    const [newType, setNewType] = useState<'interval' | 'cron' | 'run_at'>('interval');
    const [newValue, setNewValue] = useState('');

    const fetchJobs = useCallback(async () => {
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/cron/jobs`, {
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            });
            if (res.ok) {
                const data = await res.json();
                setJobs(data);
            }
        } catch (err) {
            console.error('Failed to fetch cron jobs', err);
        } finally {
            setLoading(false);
        }
    }, [accessToken]);

    useEffect(() => {
        fetchJobs();
    }, [fetchJobs]);

    const handleQuickAdd = async () => {
        if (!newName.trim() || !newValue.trim()) return;
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/cron/jobs`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: newName,
                    schedule_type: newType,
                    schedule_value: newValue,
                    payload: 'Execute scheduled task',
                    enabled: true
                }),
                credentials: 'include'
            });
            if (res.ok) {
                setNewName('');
                setNewValue('');
                fetchJobs();
                triggerToast('Job added successfully');
            }
        } catch (err) { }
    };

    const triggerToast = (msg: string) => {
        setShowToast(msg);
        setTimeout(() => setShowToast(null), 3000);
    };

    const toggleEnable = async (job: CronJob) => {
        try {
            await fetch(`${DAEMON_URL}/api/v1/cron/jobs/${job.id}`, {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: !job.enabled }),
                credentials: 'include'
            });
            fetchJobs();
            triggerToast(job.enabled ? 'Job paused' : 'Job resumed');
        } catch (err) { }
    };

    const forceRun = async (id: number) => {
        try {
            await fetch(`${DAEMON_URL}/api/v1/cron/jobs/${id}/run`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            });
            triggerToast('Job dispatched as Task');
        } catch (err) { }
    };

    const deleteJob = async (id: number) => {
        if (!confirm('Delete this scheduled job?')) return;
        try {
            await fetch(`${DAEMON_URL}/api/v1/cron/jobs/${id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            });
            fetchJobs();
            triggerToast('Job deleted');
        } catch (err) { }
    };

    const filteredJobs = jobs.filter(job => {
        if (statusFilter === 'active' && !job.enabled) return false;
        if (statusFilter === 'paused' && job.enabled) return false;
        if (typeFilter !== 'ALL' && job.schedule_type !== typeFilter) return false;
        if (searchTerm && !job.name.toLowerCase().includes(searchTerm.toLowerCase())) return false;
        return true;
    });

    if (editingJob) {
        return <CronJobForm job={editingJob} onSave={() => { setEditingJob(null); fetchJobs(); }} onCancel={() => setEditingJob(null)} />;
    }

    if (showHistory) {
        return (
            <div className="flex flex-col h-full bg-glass-pressed rounded-2xl overflow-hidden border border-glass-edge p-6">
                <div className="flex items-center justify-between mb-6">
                    <h3 className="text-xl font-bold flex items-center gap-3">
                        <History className="text-accent" /> Run History
                    </h3>
                    <button onClick={() => setShowHistory(false)} className="glass-btn px-4 py-2">Back to Jobs</button>
                </div>
                <div className="flex-1 overflow-y-auto">
                    <CronRunHistory />
                </div>
            </div>
        );
    }

    return (
        <div style={{
            maxWidth: 800, width: '100%', margin: '0 auto',
            display: 'flex', flexDirection: 'column', height: '100%',
            position: 'relative',
        }} className="animate-in fade-in duration-500">

            {/* Toast Overlay */}
            {showToast && (
                <div style={{
                    position: 'absolute', top: 12, right: 12, zIndex: 100,
                    background: 'var(--liquid-accent)', backdropFilter: 'blur(20px) saturate(180%)',
                    WebkitBackdropFilter: 'blur(20px) saturate(180%)',
                    border: '0.5px solid var(--liquid-accent-edge)',
                    color: 'var(--accent)',
                    fontSize: 12, fontWeight: 500, padding: '8px 14px',
                    borderRadius: 8, boxShadow: 'var(--liquid-inner-glow), var(--glass-shadow)',
                    animation: 'nudgeIn 0.3s ease forwards',
                }}>
                    {showToast}
                </div>
            )}

            {/* Header Mirroring TaskPanel */}
            <div style={{ marginBottom: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                    <div className="flex flex-col">
                        <h3 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>Crons</h3>
                        <span style={{ fontSize: 11, color: 'var(--text-tertiary)', fontWeight: 500 }}>Deterministic Schedulers</span>
                    </div>
                    <div className="flex gap-2">
                        <button onClick={() => setShowHistory(true)} className="glass-btn flex items-center gap-2 px-3 py-1.5 text-xs">
                            <History size={14} /> History
                        </button>
                    </div>
                </div>

                {/* Filters Mirroring TaskPanel */}
                <div style={{
                    display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'flex-end',
                    padding: 14, borderRadius: 12,
                    background: 'var(--fill-quaternary)',
                    border: '1px solid var(--separator)',
                    boxShadow: 'var(--liquid-inner-glow)',
                }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Status</span>
                        <div style={{ display: 'flex', gap: 2, background: 'var(--fill-quaternary)', borderRadius: 10, padding: 3, border: '1px solid var(--separator)' }}>
                            {['all', 'active', 'paused'].map(s => (
                                <button key={s} onClick={() => setStatusFilter(s as any)} style={{
                                    padding: '5px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600,
                                    border: 'none', cursor: 'pointer',
                                    background: statusFilter === s ? 'var(--glass-bg-hover)' : 'transparent',
                                    color: statusFilter === s ? 'var(--accent)' : 'var(--text-tertiary)',
                                    boxShadow: statusFilter === s ? 'var(--glass-shadow-sm)' : 'none',
                                    transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)', textTransform: 'capitalize',
                                }}>{s}</button>
                            ))}
                        </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Trigger Type</span>
                        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="glass-input" style={{ fontSize: 12, padding: '6px 10px', width: 'auto', borderRadius: 10 }}>
                            <option value="ALL">All Types</option>
                            <option value="interval">Interval (min)</option>
                            <option value="cron">Cron Expression</option>
                            <option value="run_at">One-shot (ISO)</option>
                        </select>
                    </div>
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6, minWidth: 150 }}>
                        <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Search Jobs</span>
                        <div className="relative">
                            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
                            <input
                                value={searchTerm}
                                onChange={e => setSearchTerm(e.target.value)}
                                placeholder="Find by name..."
                                className="glass-input w-full"
                                style={{ fontSize: 12, padding: '6px 12px 6px 32px', borderRadius: 10 }}
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* Cron List Mirroring Task List Style */}
            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16, paddingRight: 4 }} className="scrollbar-hide">
                {loading ? (
                    <div className="flex items-center justify-center h-48 opacity-40 font-mono text-xs tracking-widest animate-pulse">SYNCING_CRON_MANIFOLD...</div>
                ) : filteredJobs.length === 0 ? (
                    <div className="flex flex-col items-center justify-center p-20 gap-4 opacity-30 border-2 border-dashed border-glass-edge rounded-2xl">
                        <CalendarDays size={40} />
                        <span className="text-sm font-medium">No schedulers match your current filter</span>
                    </div>
                ) : (
                    filteredJobs.map((job) => (
                        <div key={job.id} style={{
                            display: 'flex', alignItems: 'center', gap: 16,
                            padding: '12px 16px',
                            borderRadius: 14,
                            border: `1px solid ${job.enabled ? 'var(--glass-edge)' : 'var(--separator)'}`,
                            background: job.enabled ? 'var(--glass-bg)' : 'var(--fill-quaternary)',
                            opacity: job.enabled ? 1 : 0.7,
                            transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
                            boxShadow: job.enabled ? 'var(--glass-shadow-sm)' : 'none',
                        }} className="group hover:scale-[1.005] hover:border-accent/30">

                            <button onClick={() => toggleEnable(job)} style={{
                                width: 28, height: 28, borderRadius: 8,
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                background: job.enabled ? 'var(--accent-tint)' : 'var(--fill-tertiary)',
                                color: job.enabled ? 'var(--accent)' : 'var(--text-tertiary)',
                                border: 'none', cursor: 'pointer', transition: 'all 0.2s'
                            }}>
                                {job.enabled ? <Pause size={14} /> : <Play size={14} />}
                            </button>

                            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4, minWidth: 0 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                    <span style={{
                                        fontSize: 14, fontWeight: 700, fontFamily: 'var(--font-mono)',
                                        color: job.enabled ? 'var(--text-primary)' : 'var(--text-secondary)',
                                        letterSpacing: '-0.01em'
                                    }}>{job.name}</span>
                                    <div style={{
                                        fontSize: 9, fontWeight: 700, padding: '1px 6px', borderRadius: 4,
                                        border: '1px solid var(--separator)', background: 'var(--fill-quaternary)',
                                        color: 'var(--text-tertiary)', textTransform: 'uppercase'
                                    }}>{job.schedule_type}</div>
                                </div>
                                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                                    <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--accent)', fontWeight: 600 }}>
                                        {job.schedule_value}
                                    </span>
                                    <span style={{ fontSize: 10, color: 'var(--text-tertiary)', fontWeight: 500 }}>
                                        Last: {job.last_run_at ? new Date(job.last_run_at).toLocaleString() : 'Never'}
                                    </span>
                                </div>
                            </div>

                            <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button onClick={() => forceRun(job.id)} className="p-2 glass-btn text-accent" title="Trigger Manually">
                                    <Rocket size={14} />
                                </button>
                                <button onClick={() => setEditingJob(job)} className="p-2 glass-btn" title="Config">
                                    <Settings size={14} />
                                </button>
                                <button onClick={() => deleteJob(job.id)} className="p-2 glass-btn text-status-error" title="Discard">
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Quick Add Bottom Bar Mirroring TaskPanel */}
            <div style={{
                display: 'flex', gap: 8, alignItems: 'center',
                padding: 12, borderRadius: 12,
                background: 'var(--fill-quaternary)',
                border: '1px solid var(--separator)',
                boxShadow: 'var(--glass-shadow-lg)',
            }}>
                <select
                    value={newType}
                    onChange={(e) => setNewType(e.target.value as any)}
                    className="glass-input"
                    style={{ width: 110, fontSize: 12, padding: '6px 6px' }}
                >
                    <option value="interval">Interval</option>
                    <option value="cron">Cron Expr</option>
                    <option value="run_at">One-shot</option>
                </select>
                <input
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleQuickAdd()}
                    placeholder="Scheduler Label..."
                    className="glass-input"
                    style={{ flex: 1, fontSize: 13 }}
                />
                <input
                    value={newValue}
                    onChange={(e) => setNewValue(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleQuickAdd()}
                    placeholder={newType === 'interval' ? 'Minutes (e.g. 60)' : 'Value...'}
                    className="glass-input"
                    style={{ width: 150, fontSize: 12 }}
                />
                <button
                    onClick={handleQuickAdd}
                    className="glass-btn glass-btn--primary"
                    style={{ fontSize: 12, padding: '6px 16px', flexShrink: 0 }}
                >
                    Add Scheduler
                </button>
            </div>
        </div>
    );
};

export default CronPanel;
