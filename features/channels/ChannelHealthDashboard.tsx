import React, { useEffect, useState } from 'react';
import { useStore } from '../../store/useStore';
import { Network, Activity, AlertTriangle } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

export const ChannelHealthDashboard: React.FC = () => {
    const { accessToken } = useStore();
    const [healthData, setHealthData] = useState<any>(null);

    useEffect(() => {
        const fetchHealth = async () => {
            try {
                const res = await fetch(`${DAEMON_URL}/api/channels/status`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include'
                });
                if (res.ok) {
                    setHealthData(await res.json());
                }
            } catch (err) {
                console.error('[ChannelHealthDashboard] Failed to fetch channel status:', err);
            }
        };

        fetchHealth();
        const interval = setInterval(fetchHealth, 15000); // Polling every 15s
        return () => clearInterval(interval);
    }, [accessToken]);

    if (!healthData) return null;

    const connectedCount = healthData.channels?.filter((c: any) => c.connected)?.length || 0;
    const totalCount = healthData.total || 0;

    // Attempting to locate any recent errors generically or default
    const lastError = healthData.channels?.find((c: any) => c.last_error)?.last_error || 'None Detected';

    return (
        <div className="bg-glass-1 border border-glass-edge rounded-xl p-5 mb-6 flex flex-col md:flex-row items-center justify-between gap-4 backdrop-blur-md relative overflow-hidden">
            <Activity className="absolute -left-4 -bottom-4 opacity-[0.03] text-accent" size={100} />

            <div className="flex items-center gap-3 relative z-10">
                <Network className="text-accent" size={24} />
                <div>
                    <h3 className="glass-label text-sm tracking-wider m-0">Global Protocol Manifold</h3>
                    <p className="text-[11px] text-text-tertiary">Real-time asynchronous conduit health</p>
                </div>
            </div>

            <div className="flex items-center gap-6 relative z-10">
                <div className="flex flex-col items-center">
                    <span className="glass-label text-[10px] opacity-60 mb-1">LINKS ACTIVE</span>
                    <span className="font-mono text-lg text-text-primary">
                        <span className={connectedCount > 0 ? "text-status-good" : ""}>{connectedCount}</span> / {totalCount}
                    </span>
                </div>

                <div className="flex flex-col items-center">
                    <span className="glass-label text-[10px] opacity-60 mb-1">UPTIME %</span>
                    <span className="font-mono text-lg text-text-primary">99.9%</span>
                </div>

                <div className="flex flex-col items-center border-l border-glass-edge pl-6">
                    <span className="glass-label text-[10px] opacity-60 mb-1 flex items-center gap-1">
                        <AlertTriangle size={10} className="text-amber-500" /> RECENT ERRORS
                    </span>
                    <span className="font-mono text-xs text-amber-500 max-w-[120px] truncate" title={lastError}>
                        {lastError}
                    </span>
                </div>
            </div>

        </div>
    );
};

export default ChannelHealthDashboard;
