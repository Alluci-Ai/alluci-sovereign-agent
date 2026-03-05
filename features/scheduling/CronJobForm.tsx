import React, { useState } from 'react';
import { useStore } from '../../store/useStore';
import { Save, X, Activity, Server, ArrowRight, Clock, Target, Shield } from 'lucide-react';
import { CronJob } from './CronPanel';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

interface CronJobFormProps {
    job: Partial<CronJob>;
    onSave: () => void;
    onCancel: () => void;
}

export const CronJobForm: React.FC<CronJobFormProps> = ({ job, onSave, onCancel }) => {
    const { accessToken } = useStore();
    const [formData, setFormData] = useState<Partial<CronJob>>(job);
    const [saving, setSaving] = useState(false);

    const update = (field: keyof CronJob, value: any) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const handleSave = async () => {
        if (!formData.name || !formData.schedule_value || !formData.payload) {
            alert("Name, Schedule, and Task Payload are required.");
            return;
        }

        setSaving(true);
        try {
            const isUpdate = !!formData.id;
            const url = isUpdate ? `${DAEMON_URL}/api/cron/jobs/${formData.id}` : `${DAEMON_URL}/api/cron/jobs`;
            const method = isUpdate ? 'PUT' : 'POST';

            const res = await fetch(url, {
                method,
                headers: { 'Authorization': `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
                body: JSON.stringify(formData),
                credentials: 'include'
            });

            if (res.ok) onSave();
            else throw new Error('Save failed');
        } catch (err) {
            console.error(err);
            alert("Failed to save job configuration");
        } finally {
            setSaving(false);
        }
    };

    return (
        <div style={{
            maxWidth: 600, width: '100%', margin: '0 auto',
            display: 'flex', flexDirection: 'column', height: '100%',
        }} className="animate-in slide-in-from-bottom-8 duration-500">

            <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '24px 0', marginBottom: 12
            }}>
                <div className="flex flex-col">
                    <h3 style={{ fontSize: 24, fontWeight: 800, letterSpacing: '-0.03em', color: 'var(--text-primary)' }}>
                        {formData.id ? 'Refine Scheduler' : 'New Scheduler'}
                    </h3>
                    <span style={{ fontSize: 11, color: 'var(--text-tertiary)', fontWeight: 500 }}>Configuring deterministic trigger boundary</span>
                </div>
                <button onClick={onCancel} className="p-2 rounded-full hover:bg-glass-bg-hover transition-colors">
                    <X size={20} className="text-text-tertiary" />
                </button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', paddingRight: 4 }} className="scrollbar-hide flex flex-col gap-6 pb-24">

                {/* Identity Section */}
                <div style={{
                    padding: 24, borderRadius: 20, background: 'var(--glass-bg)',
                    border: '1px solid var(--glass-edge)', boxShadow: 'var(--glass-shadow-lg)'
                }}>
                    <h4 style={{
                        fontSize: 10, fontWeight: 800, color: 'var(--accent)',
                        textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 20,
                        display: 'flex', alignItems: 'center', gap: 8
                    }}>
                        <Activity size={12} /> Trigger Identity
                    </h4>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                            <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)' }}>Functional Label</label>
                            <input
                                value={formData.name || ''}
                                onChange={e => update('name', e.target.value)}
                                className="glass-input"
                                style={{ fontSize: 14, padding: '10px 14px', borderRadius: 12 }}
                                placeholder="e.g. Daily Cognitive Synthesis"
                            />
                        </div>

                        <div style={{ display: 'flex', gap: 16 }}>
                            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                                <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)' }}>Schedule Type</label>
                                <select
                                    value={formData.schedule_type || 'interval'}
                                    onChange={e => update('schedule_type', e.target.value)}
                                    className="glass-input"
                                    style={{ fontSize: 13, padding: '10px 14px', borderRadius: 12 }}
                                >
                                    <option value="interval">Interval (Minutes)</option>
                                    <option value="cron">Cron Expression</option>
                                    <option value="run_at">One-Shot (ISO)</option>
                                </select>
                            </div>
                            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
                                <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)' }}>Trigger Value</label>
                                <div className="relative">
                                    <Clock size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-accent opacity-50" />
                                    <input
                                        value={formData.schedule_value || ''}
                                        onChange={e => update('schedule_value', e.target.value)}
                                        className="glass-input w-full"
                                        style={{ fontSize: 14, padding: '10px 14px 10px 34px', borderRadius: 12, fontFamily: 'var(--font-mono)' }}
                                        placeholder={formData.schedule_type === 'cron' ? '0 0 * * *' : '60'}
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Objective Section */}
                <div style={{
                    padding: 24, borderRadius: 20, background: 'var(--glass-bg)',
                    border: '1px solid var(--glass-edge)', boxShadow: 'var(--glass-shadow-lg)'
                }}>
                    <h4 style={{
                        fontSize: 10, fontWeight: 800, color: 'var(--status-good)',
                        textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 20,
                        display: 'flex', alignItems: 'center', gap: 8
                    }}>
                        <Target size={12} /> Task Dispatch Objective
                    </h4>
                    <span style={{ fontSize: 11, color: 'var(--text-tertiary)', display: 'block', marginBottom: 12 }}>
                        Definition of the autonomous intent to be injected into the task manifold.
                    </span>
                    <textarea
                        value={formData.payload || ''}
                        onChange={e => update('payload', e.target.value)}
                        className="glass-input"
                        style={{
                            fontSize: 13, padding: 16, borderRadius: 12, width: '100%',
                            minHeight: 120, resize: 'none', lineHeight: 1.6,
                            background: 'var(--fill-quaternary)'
                        }}
                        placeholder="I want you to analyze system telemetry and..."
                    />
                </div>

                {/* Overrides Section */}
                <div style={{
                    padding: 24, borderRadius: 20, background: 'var(--glass-bg)',
                    border: '1px solid var(--glass-edge)', boxShadow: 'var(--glass-shadow-lg)'
                }}>
                    <h4 style={{
                        fontSize: 10, fontWeight: 800, color: 'var(--status-warning)',
                        textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 20,
                        display: 'flex', alignItems: 'center', gap: 8
                    }}>
                        <Shield size={12} /> Execution Boundary Overrides
                    </h4>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                            <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)' }}>Model Constraint</label>
                            <input
                                value={formData.model_override || ''}
                                onChange={e => update('model_override', e.target.value)}
                                className="glass-input"
                                style={{ fontSize: 12, padding: '8px 12px', borderRadius: 10 }}
                                placeholder="Inherit System Logic"
                            />
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                            <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)' }}>Thinking Depth</label>
                            <select
                                value={formData.thinking_level || ''}
                                onChange={e => update('thinking_level', e.target.value)}
                                className="glass-input"
                                style={{ fontSize: 12, padding: '8px 12px', borderRadius: 10 }}
                            >
                                <option value="">Auto (Default)</option>
                                <option value="low">Efficiency (Low)</option>
                                <option value="medium">Standard (Med)</option>
                                <option value="high">Complex (High)</option>
                            </select>
                        </div>
                    </div>

                    <div style={{ marginTop: 20, padding: 16, borderRadius: 14, background: 'var(--fill-quaternary)', border: '1px solid var(--separator)' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                            <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Delivery Routing (Optional)</label>
                            <select
                                className="glass-input"
                                style={{ fontSize: 12, padding: '8px 10px', borderRadius: 10 }}
                                value={formData.delivery_mode || 'none'}
                                onChange={e => update('delivery_mode', e.target.value)}
                            >
                                <option value="none">No External Routing</option>
                                <option value="announce-summary">Summary Announcement</option>
                                <option value="post-transcript">Full Transcript</option>
                            </select>

                            {formData.delivery_mode !== 'none' && (
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }} className="animate-in slide-in-from-top-2">
                                    <input
                                        className="glass-input" style={{ fontSize: 11, padding: '8px 10px', borderRadius: 10 }}
                                        placeholder="Channel (e.g. telegram)"
                                        value={formData.delivery_channel || ''} onChange={e => update('delivery_channel', e.target.value)}
                                    />
                                    <input
                                        className="glass-input" style={{ fontSize: 11, padding: '8px 10px', borderRadius: 10 }}
                                        placeholder="Target Recipient"
                                        value={formData.delivery_to || ''} onChange={e => update('delivery_to', e.target.value)}
                                    />
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom Bar */}
            <div style={{
                position: 'absolute', bottom: 0, left: 0, right: 0,
                padding: '20px 0', borderTop: '1px solid var(--separator)',
                display: 'flex', justifyContent: 'flex-end', gap: 12,
                background: 'linear-gradient(to top, var(--bg-primary) 80%, transparent)'
            }}>
                <button
                    onClick={onCancel}
                    className="glass-btn"
                    style={{ padding: '0 24px', height: 44, borderRadius: 14, fontSize: 14, fontWeight: 600 }}
                >
                    Discard Changes
                </button>
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="glass-btn glass-btn--primary"
                    style={{ padding: '0 32px', height: 44, borderRadius: 14, fontSize: 14, fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}
                >
                    {saving ? <Activity size={18} className="animate-spin" /> : <Save size={18} />}
                    {saving ? 'Synchronizing...' : 'Save Configuration'}
                </button>
            </div>
        </div>
    );
};

export default CronJobForm;
