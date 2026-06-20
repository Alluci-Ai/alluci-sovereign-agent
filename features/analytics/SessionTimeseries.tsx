import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useStore } from '../../store/useStore';
import { Activity } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

interface SessionTimeseriesProps {
    sessionKey: string;
}

export const SessionTimeseries: React.FC<SessionTimeseriesProps> = ({ sessionKey }) => {
    const { accessToken } = useStore();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [data, setData] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchTimeseries = async () => {
            setLoading(true);
            try {
                const res = await fetch(`${DAEMON_URL}/api/v1/usage/sessions/${sessionKey}/timeseries`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include',
                });
                if (res.ok) {
                    const timeseries = await res.json();

                    // Format data for chart
                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                    const chartData = timeseries.map((t: any, idx: number) => ({
                        turn: `Turn ${idx + 1}`,
                        tokens: t.input_tokens + t.output_tokens,
                        cost: t.turn_cost,
                        model: t.model
                    }));

                    setData(chartData);
                }
            } catch (err) {
                console.error('[SessionTimeseries] Failed formatting usage series:', err);
            } finally {
                setLoading(false);
            }
        };

        if (sessionKey) {
            fetchTimeseries();
        }
    }, [sessionKey, accessToken]);

    return (
        <div className="bg-glass-1 border border-glass-edge rounded-xl p-5 flex flex-col gap-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Activity size={16} className="text-accent" />
                    <h3 className="glass-label text-sm tracking-wider">Turn Architecture</h3>
                </div>
                <div className="text-[10px] font-mono opacity-50">{sessionKey.slice(0, 8)}</div>
            </div>

            {loading ? (
                <div className="h-48 flex items-center justify-center text-xs opacity-50 font-mono tracking-widest animate-pulse">
                    LOADING_MANIFOLD_SERIES...
                </div>
            ) : data.length === 0 ? (
                <div className="h-48 flex items-center justify-center text-xs opacity-50">
                    No timeline activity recorded yet
                </div>
            ) : (
                <div className="h-48 w-full mt-2">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                            <XAxis
                                dataKey="turn"
                                tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.4)' }}
                                axisLine={false}
                                tickLine={false}
                            />
                            <YAxis
                                tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.4)' }}
                                axisLine={false}
                                tickLine={false}
                                tickFormatter={(val) => `${val}`}
                            />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: 'rgba(20,20,20,0.8)',
                                    border: '1px solid rgba(255,255,255,0.1)',
                                    borderRadius: '8px',
                                    backdropFilter: 'blur(10px)',
                                    fontSize: '12px'
                                }}
                            />
                            <Line
                                type="monotone"
                                dataKey="tokens"
                                stroke="#91D65F"
                                strokeWidth={2}
                                dot={{ fill: '#91D65F', r: 3, strokeWidth: 0 }}
                                activeDot={{ r: 5 }}
                                name="Tokens"
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}
        </div>
    );
};

export default SessionTimeseries;
