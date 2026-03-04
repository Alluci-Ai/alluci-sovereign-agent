import React, { useState } from 'react';
import { useStore } from '../../store/useStore';
import { Save, X, Activity, Server, ArrowRight } from 'lucide-react';
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

    // Simplistic schema-driven update
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
        <div className="flex flex-col h-full animate-in slide-in-from-bottom-4 duration-300">
            <div className="flex items-center justify-between p-4 border-b border-glass-edge bg-glass-1">
                <h3 className="text-sm font-semibold tracking-tight">
                    {formData.id ? 'Edit Scheduled Job' : 'Create Scheduled Job'}
                </h3>
                <button onClick={onCancel} className="p-1 rounded hover:bg-white/5 opacity-70 hover:opacity-100 transition-opacity">
                    <X size={16} />
                </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-5 custom-scrollbar">

                {/* Core Config */}
                <div className="bg-glass-1 border border-glass-edge p-4 rounded-xl flex flex-col gap-4">
                    <h4 className="text-[10px] font-mono tracking-widest text-text-tertiary uppercase flex items-center gap-2">
                        <Activity size={12} className="text-accent" /> Core Trigger Identity
                    </h4>

                    <div className="flex flex-col gap-1.5">
                        <label className="text-[11px] text-text-secondary pl-1">Job Name</label>
                        <input
                            value={formData.name || ''}
                            onChange={e => update('name', e.target.value)}
                            className="glass-input text-xs"
                            placeholder="e.g. Daily Data Backup"
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="flex flex-col gap-1.5">
                            <label className="text-[11px] text-text-secondary pl-1">Schedule Type</label>
                            <select
                                value={formData.schedule_type || 'interval'}
                                onChange={e => update('schedule_type', e.target.value)}
                                className="glass-input text-xs"
                            >
                                <option value="interval">Interval (Minutes)</option>
                                <option value="cron">Cron Expression</option>
                                <option value="run_at">One-Shot (ISO Datetime)</option>
                            </select>
                        </div>
                        <div className="flex flex-col gap-1.5">
                            <label className="text-[11px] text-text-secondary pl-1">Trigger Value</label>
                            <input
                                value={formData.schedule_value || ''}
                                onChange={e => update('schedule_value', e.target.value)}
                                className="glass-input text-xs font-mono"
                                placeholder={formData.schedule_type === 'cron' ? '0 0 * * *' : '60'}
                            />
                        </div>
                    </div>
                </div>

                {/* Dispatch Context */}
                <div className="bg-glass-1 border border-glass-edge p-4 rounded-xl flex flex-col gap-4">
                    <h4 className="text-[10px] font-mono tracking-widest text-text-tertiary uppercase flex items-center gap-2">
                        <ArrowRight size={12} className="text-status-good" /> Task Dispatch Payload
                    </h4>

                    <p className="text-[10px] text-text-tertiary mb-1">
                        When this cron triggers, what objective should be dispatched into the event-driven task queue?
                    </p>

                    <textarea
                        value={formData.payload || ''}
                        onChange={e => update('payload', e.target.value)}
                        className="glass-input text-xs h-24 resize-none font-mono"
                        placeholder="Analyze system usage over the last 24 hours and generate a summary report."
                    />
                </div>

                {/* Overrides & Delivery */}
                <div className="bg-glass-1 border border-glass-edge p-4 rounded-xl flex flex-col gap-4">
                    <h4 className="text-[10px] font-mono tracking-widest text-text-tertiary uppercase flex items-center gap-2">
                        <Server size={12} className="text-status-warning" /> Advanced Execution Limits
                    </h4>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="flex flex-col gap-1.5">
                            <label className="text-[11px] text-text-secondary pl-1">Model Override</label>
                            <input
                                value={formData.model_override || ''}
                                onChange={e => update('model_override', e.target.value)}
                                className="glass-input text-xs"
                                placeholder="e.g. models/gemini-2.5-pro"
                            />
                        </div>
                        <div className="flex flex-col gap-1.5">
                            <label className="text-[11px] text-text-secondary pl-1">Thinking Level Override</label>
                            <select
                                value={formData.thinking_level || ''}
                                onChange={e => update('thinking_level', e.target.value)}
                                className="glass-input text-xs"
                            >
                                <option value="">(Inherit Agent Default)</option>
                                <option value="low">Low / Fast</option>
                                <option value="medium">Medium</option>
                                <option value="high">High / Deep</option>
                            </select>
                        </div>
                    </div>

                    <div className="border border-glass-edge rounded-lg p-3 bg-glass-2 mt-2">
                        <div className="flex-1 flex flex-col gap-3">
                            <label className="text-[11px] text-text-secondary">Delivery Routing Output</label>
                            <div className="flex items-center gap-2">
                                <select
                                    className="glass-input text-xs flex-1"
                                    value={formData.delivery_mode || 'none'}
                                    onChange={e => update('delivery_mode', e.target.value)}
                                >
                                    <option value="none">No External Delivery</option>
                                    <option value="announce-summary">Send Summary Announcement</option>
                                    <option value="post-transcript">Send Full Data Transcript</option>
                                </select>
                            </div>

                            {formData.delivery_mode !== 'none' && (
                                <div className="grid grid-cols-2 gap-2 mt-1 animate-in slide-in-from-top-2 duration-200">
                                    <input
                                        className="glass-input text-[11px] font-mono" placeholder="Adapter (e.g. discord)"
                                        value={formData.delivery_channel || ''} onChange={e => update('delivery_channel', e.target.value)}
                                    />
                                    <input
                                        className="glass-input text-[11px] font-mono" placeholder="Recipient ID"
                                        value={formData.delivery_to || ''} onChange={e => update('delivery_to', e.target.value)}
                                    />
                                </div>
                            )}
                        </div>
                    </div>
                </div>

            </div>

            <div className="p-4 bg-glass-pressed border-t border-glass-edge flex justify-end gap-3 flex-shrink-0">
                <button onClick={onCancel} className="glass-btn text-xs px-4">Cancel</button>
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="glass-btn glass-btn--primary text-xs px-6 flex items-center gap-2"
                >
                    <Save size={14} /> {saving ? 'Committing...' : 'Commit Save'}
                </button>
            </div>
        </div>
    );
};

export default CronJobForm;
