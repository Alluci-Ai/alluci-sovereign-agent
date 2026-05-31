import React, { useEffect, useState } from 'react';
import { useStore } from '../../store/useStore';
import { Activity, Database, Key, Network, Cpu, RefreshCw } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://127.0.0.1:8000';

interface HealthPayload {
    database: string;
    vault: string;
    model_router: string;
    cron_engine: string;
}

export const SystemHealthCard: React.FC = () => {
    const { accessToken } = useStore();
    const [health, setHealth] = useState<HealthPayload | null>(null);
    const [loading, setLoading] = useState(true);

    const checkHealth = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/system/health`, {
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            });
            if (res.ok) {
                setHealth(await res.json());
            }
        } catch (err) {
            console.error('[SystemHealthCard] Failed running diagnostic check:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        checkHealth();
        // Check health periodically every 30s
        const interval = setInterval(checkHealth, 30000);
        return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [accessToken]);

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'healthy': return <span className="w-2 h-2 rounded-full bg-status-good shadow-[0_0_8px_var(--status-good-rgb)]" title="Healthy" />;
            case 'warning': return <span className="w-2 h-2 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]" title="Warning / Degraded" />;
            case 'unhealthy': default: return <span className="w-2 h-2 rounded-full bg-status-error shadow-[0_0_8px_var(--status-error-rgb)]" title="Failing" />;
        }
    };

    return (
        <div className="bg-glass-1 border border-glass-edge rounded-xl p-5 flex flex-col gap-4 relative overflow-hidden">
            <Activity className="absolute -right-4 -bottom-4 opacity-[0.03] text-accent" size={100} />

            <div className="flex justify-between items-center pb-2 border-b border-glass-edge">
                <div className="flex items-center gap-2">
                    <Activity size={16} className="text-accent" />
                    <h3 className="glass-label text-sm tracking-wider">Internal Daemon Health</h3>
                </div>

                <button
                    onClick={checkHealth}
                    className={`p-1 rounded-md text-text-tertiary hover:text-accent hover:bg-glass-edge transition-all ${loading ? 'animate-spin opacity-50' : ''}`}
                    title="Run Diagnostics"
                >
                    <RefreshCw size={14} />
                </button>
            </div>

            <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center justify-between col-span-1 border border-glass-edge rounded-lg p-3 bg-glass-2">
                    <div className="flex items-center gap-2">
                        <Database size={14} className="text-text-secondary" />
                        <span className="text-[11px] glass-label text-text-primary tracking-wide">Database Schema</span>
                    </div>
                    {getStatusIcon(health?.database || 'unhealthy')}
                </div>

                <div className="flex items-center justify-between col-span-1 border border-glass-edge rounded-lg p-3 bg-glass-2">
                    <div className="flex items-center gap-2">
                        <Key size={14} className="text-text-secondary" />
                        <span className="text-[11px] glass-label text-text-primary tracking-wide">API Vault Ledger</span>
                    </div>
                    {getStatusIcon(health?.vault || 'unhealthy')}
                </div>

                <div className="flex items-center justify-between col-span-1 border border-glass-edge rounded-lg p-3 bg-glass-2">
                    <div className="flex items-center gap-2">
                        <Network size={14} className="text-text-secondary" />
                        <span className="text-[11px] glass-label text-text-primary tracking-wide">Model Router Ring</span>
                    </div>
                    {getStatusIcon(health?.model_router || 'unhealthy')}
                </div>

                <div className="flex items-center justify-between col-span-1 border border-glass-edge rounded-lg p-3 bg-glass-2">
                    <div className="flex items-center gap-2">
                        <Cpu size={14} className="text-text-secondary" />
                        <span className="text-[11px] glass-label text-text-primary tracking-wide">App Cron Engine</span>
                    </div>
                    {getStatusIcon(health?.cron_engine || 'unhealthy')}
                </div>
            </div>

            <div className="text-[9px] glass-label text-text-tertiary mt-1 opacity-50 flex justify-end tracking-wider uppercase">
                AUTOMATED_TELEMETRY_CHECKS_ACTIVE
            </div>
        </div>
    );
};

export default SystemHealthCard;
