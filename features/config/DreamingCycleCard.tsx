import React, { useEffect, useState } from 'react';
import { useStore } from '../../store/useStore';
import { Moon, Play, Clock, Globe, Shield, RefreshCw, CheckCircle2 } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

interface DreamingStatus {
    enabled: boolean;
    schedule_time: string;
    timezone: string;
    max_duration_minutes: number;
    yield_on_user_activity: boolean;
    detected_host_timezone?: {
        timezone_name: string;
        tz_abbr: string;
        utc_offset: string;
        local_time_str: string;
    };
    is_active: boolean;
}

export const DreamingCycleCard: React.FC = () => {
    const { accessToken } = useStore();
    const [status, setStatus] = useState<DreamingStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [triggering, setTriggering] = useState(false);
    const [triggerMessage, setTriggerMessage] = useState<string | null>(null);

    const fetchStatus = async () => {
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/config/dreaming/status`, {
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            });
            if (res.ok) {
                const data = await res.json();
                setStatus(data);
            }
        } catch (err) {
            console.error('[DreamingCycleCard] Failed to fetch status:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStatus();
        const interval = setInterval(fetchStatus, 10000);
        return () => clearInterval(interval);
    }, [accessToken]);

    const handleTriggerManual = async () => {
        setTriggering(true);
        setTriggerMessage(null);
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/config/dreaming/trigger`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                },
                credentials: 'include'
            });
            const data = await res.json();
            setTriggerMessage(data.message || 'Dreaming Cycle initiated.');
            fetchStatus();
        } catch (err: any) {
            setTriggerMessage(`Trigger error: ${err.message}`);
        } finally {
            setTriggering(false);
        }
    };

    const tz = status?.detected_host_timezone;

    return (
        <div className="bg-glass-1 border border-glass-edge rounded-xl p-5 flex flex-col gap-4 text-text-primary shadow-sm">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                        <Moon size={18} />
                    </div>
                    <div>
                        <h3 className="text-sm font-semibold tracking-tight text-text-primary">
                            Offline Dreaming Cycle & LoRA Forge
                        </h3>
                        <p className="text-xs text-text-tertiary">
                            Autonomous overnight self-instruct and preference harvesting distillation
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono font-medium ${status?.is_active ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30 animate-pulse' : 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${status?.is_active ? 'bg-amber-400' : 'bg-emerald-400'}`} />
                        {status?.is_active ? 'CYCLE ACTIVE (GPU IN USE)' : 'STANDBY / IDLE'}
                    </span>
                </div>
            </div>

            {loading ? (
                <div className="p-4 text-xs font-mono opacity-50 animate-pulse">
                    SCANNING_HOST_TIMEZONE_AND_HARDWARE...
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    {/* Timezone & Host Scan */}
                    <div className="bg-glass-2 border border-glass-edge rounded-lg p-3 flex flex-col justify-between">
                        <div className="flex items-center gap-2 text-text-secondary text-xs font-medium mb-1">
                            <Globe size={14} className="text-indigo-400" />
                            Detected Host Timezone
                        </div>
                        <div className="text-sm font-mono font-semibold text-text-primary">
                            {tz ? `${tz.tz_abbr} (${tz.utc_offset})` : 'Local Time'}
                        </div>
                        <div className="text-[10px] text-text-tertiary mt-1 font-mono">
                            Host Local: {tz?.local_time_str?.split(' ')[1] || '--:--:--'}
                        </div>
                    </div>

                    {/* Schedule Time & Duration */}
                    <div className="bg-glass-2 border border-glass-edge rounded-lg p-3 flex flex-col justify-between">
                        <div className="flex items-center gap-2 text-text-secondary text-xs font-medium mb-1">
                            <Clock size={14} className="text-emerald-400" />
                            Scheduled Time & Cap
                        </div>
                        <div className="text-sm font-mono font-semibold text-text-primary">
                            {status?.schedule_time || '02:00'} Local Time
                        </div>
                        <div className="text-[10px] text-text-tertiary mt-1">
                            Max Duration: {status?.max_duration_minutes || 45} mins
                        </div>
                    </div>

                    {/* GPU Preemption Policy */}
                    <div className="bg-glass-2 border border-glass-edge rounded-lg p-3 flex flex-col justify-between">
                        <div className="flex items-center gap-2 text-text-secondary text-xs font-medium mb-1">
                            <Shield size={14} className="text-amber-400" />
                            GPU Lock Policy
                        </div>
                        <div className="text-sm font-mono font-semibold text-emerald-400">
                            {status?.yield_on_user_activity ? 'Preemptive Yield' : 'Non-Preemptive'}
                        </div>
                        <div className="text-[10px] text-text-tertiary mt-1">
                            Zero chat latency on user arrival
                        </div>
                    </div>
                </div>
            )}

            <div className="flex items-center justify-between pt-2 border-t border-glass-edge">
                <div className="text-xs text-text-tertiary flex items-center gap-1.5">
                    {triggerMessage ? (
                        <span className="text-emerald-400 flex items-center gap-1">
                            <CheckCircle2 size={13} /> {triggerMessage}
                        </span>
                    ) : (
                        <span>Configurable via Daemon Settings below (`DREAMING_CYCLE_TIME`).</span>
                    )}
                </div>

                <button
                    onClick={handleTriggerManual}
                    disabled={triggering || status?.is_active}
                    className="glass-btn text-xs flex items-center gap-2 px-3 py-1.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20 transition-all disabled:opacity-50"
                >
                    {triggering ? (
                        <>
                            <RefreshCw size={13} className="animate-spin" />
                            Initiating...
                        </>
                    ) : (
                        <>
                            <Play size={13} />
                            Trigger Manual Dreaming Cycle
                        </>
                    )}
                </button>
            </div>
        </div>
    );
};

export default DreamingCycleCard;
