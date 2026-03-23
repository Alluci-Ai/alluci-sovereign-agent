import React, { useEffect, useState } from 'react';
import { useStore } from '../../store/useStore';
import { Coins, Layers } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://127.0.0.1:8000';

interface SessionMetrics {
    input_tokens: number;
    output_tokens: number;
    cumulative_cost: number;
    turn_count: number;
}

/**
 * SessionCostDisplay — Cost summary dashboard parsing total usage overhead
 * natively fetched directly out of the `analytics.py` `get_session_timeseries` pipeline.
 */
export const SessionCostDisplay: React.FC = () => {
    const { activeSessionKey, accessToken } = useStore();
    const [metrics, setMetrics] = useState<SessionMetrics>({
        input_tokens: 0,
        output_tokens: 0,
        cumulative_cost: 0,
        turn_count: 0
    });

    useEffect(() => {
        const fetchCosts = async () => {
            try {
                const res = await fetch(`${DAEMON_URL}/api/v1/usage/sessions/${activeSessionKey}/timeseries`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include',
                });
                if (res.ok) {
                    const series = await res.json();
                    if (series.length > 0) {
                        const aggregate = series.reduce((acc: any, cur: any) => ({
                            input_tokens: acc.input_tokens + cur.input_tokens,
                            output_tokens: acc.output_tokens + cur.output_tokens,
                            turn_count: acc.turn_count + 1
                        }), { input_tokens: 0, output_tokens: 0, turn_count: 0 });

                        // Grab cumulative absolute ceiling
                        const ceiling = series[series.length - 1];
                        setMetrics({
                            ...aggregate,
                            cumulative_cost: ceiling.cumulative_cost
                        });
                    } else {
                        setMetrics({ input_tokens: 0, output_tokens: 0, cumulative_cost: 0, turn_count: 0 });
                    }
                }
            } catch (err) {
                console.error('[SessionCostDisplay] Failed parsing run metrics:', err);
            }
        };

        if (activeSessionKey) {
            fetchCosts();
        }
    }, [activeSessionKey, accessToken]);

    return (
        <div className="bg-glass-1 border border-glass-edge rounded-xl p-4 flex flex-col gap-4">
            <div className="flex items-center gap-2 mb-2">
                <Coins size={16} className="text-accent" />
                <h3 className="glass-label text-xs tracking-wider">Metrics & Economy</h3>
            </div>

            <div className="grid grid-cols-2 gap-3">
                <div className="flex flex-col gap-1">
                    <span className="glass-label text-[9px] text-text-tertiary uppercase">Input Load</span>
                    <span className="text-text-primary text-[14px] font-mono tracking-tighter">
                        {metrics.input_tokens.toLocaleString()} <span className="text-[9px] opacity-40">TKN</span>
                    </span>
                </div>

                <div className="flex flex-col gap-1">
                    <span className="glass-label text-[9px] text-text-tertiary uppercase">Inference Out</span>
                    <span className="text-text-primary text-[14px] font-mono tracking-tighter">
                        {metrics.output_tokens.toLocaleString()} <span className="text-[9px] opacity-40">TKN</span>
                    </span>
                </div>

                <div className="flex flex-col gap-1 col-span-2 pt-2 border-t border-glass-edge">
                    <span className="glass-label text-[9px] text-text-tertiary uppercase">Expenditure Overhead</span>
                    <div className="flex items-baseline gap-2">
                        <span className="text-status-good text-[20px] font-mono tracking-tighter shadow-sm blur-none">
                            ${metrics.cumulative_cost.toFixed(4)}
                        </span>
                        <span className="text-[10px] glass-label text-text-tertiary opacity-40">
                            over {metrics.turn_count} execution waves
                        </span>
                    </div>
                </div>
            </div>

            <div className="text-[8px] glass-label text-text-quaternary mt-1">
                Data generated via realtime analytical hooks embedded natively across Edge router abstractions.
            </div>
        </div>
    );
};

export default SessionCostDisplay;
