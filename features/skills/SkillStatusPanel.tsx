import React, { useState, useEffect } from 'react';
import { useStore } from '../../store/useStore';
import { Activity, AlertTriangle, CheckCircle } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

export const SkillStatusPanel: React.FC<{ skillId: string }> = ({ skillId }) => {
    const { accessToken } = useStore();
    const [status, setStatus] = useState<any>(null);

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const res = await fetch(`${DAEMON_URL}/api/v1/skills/${skillId}/status`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include'
                });
                if (res.ok) setStatus(await res.json());
            } catch (err) {
                console.error('Failed fetching skill status', err);
            }
        };
        fetchStatus();
    }, [skillId, accessToken]);

    if (!status) return <div className="text-[10px] font-mono opacity-50 text-center py-4">ANALYZING_DEPENDENCIES...</div>;

    const allGood = status.missing_deps?.length === 0 && !status.last_error;

    return (
        <div className={`mt-3 p-3 rounded-lg border flex flex-col gap-2 ${allGood ? 'bg-status-good/5 border-status-good/20' : 'bg-status-error/5 border-status-error/20'}`}>
            <h4 className="text-[10px] glass-label uppercase tracking-widest m-0 flex items-center gap-1 opacity-80">
                <Activity size={12} /> OS Health Telemetry
            </h4>

            {status.missing_deps?.length > 0 && (
                <div className="flex flex-col gap-1 mt-1">
                    <span className="text-[9px] font-mono text-status-error flex items-center gap-1">
                        <AlertTriangle size={10} /> MISSING NATIVE DEPENDENCIES
                    </span>
                    <ul className="list-disc pl-4 text-[10px] font-mono text-status-warning m-0">
                        {status.missing_deps.map((dep: string) => <li key={dep}>{dep}</li>)}
                    </ul>
                </div>
            )}

            {status.last_error && (
                <div className="flex flex-col gap-1 mt-1 bg-black/40 p-2 rounded border border-white/5">
                    <span className="text-[9px] font-mono text-status-error">EXCEPTION_TRACE</span>
                    <span className="text-[10px] font-mono opacity-80 break-words">{status.last_error}</span>
                </div>
            )}

            {allGood && (
                <div className="flex items-center gap-2 text-status-good text-[10px] font-mono mt-1">
                    <CheckCircle size={12} /> <span>DEPENDENCIES_RESOLVED</span>
                </div>
            )}
        </div>
    );
};

export default SkillStatusPanel;
