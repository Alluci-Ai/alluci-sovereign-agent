import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useStore } from '../../store/useStore';
import { BarChart3 } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

interface DailyBarChartProps {
    startDate?: string;
    endDate?: string;
}

export const DailyBarChart: React.FC<DailyBarChartProps> = ({ startDate, endDate }) => {
    const { accessToken } = useStore();
    const [data, setData] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchDaily = async () => {
            setLoading(true);
            try {
                const params = new URLSearchParams();
                if (startDate) params.append('start', startDate);
                if (endDate) params.append('end', endDate);

                const res = await fetch(`${DAEMON_URL}/api/usage/daily?${params}`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include',
                });
                if (res.ok) {
                    const series = await res.json();

                    const chartData = series.map((d: any) => ({
                        date: new Date(d.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
                        tokens: d.input_tokens + d.output_tokens,
                        cost: d.cost,
                        turns: d.turns
                    }));

                    setData(chartData);
                }
            } catch (err) {
                console.error('[DailyBarChart] Failed fetching payload:', err);
            } finally {
                setLoading(false);
            }
        };
        fetchDaily();
    }, [startDate, endDate, accessToken]);

    return (
        <div className="bg-glass-1 border border-glass-edge rounded-xl p-5 flex flex-col gap-4">
            <div className="flex items-center gap-2">
                <BarChart3 size={16} className="text-accent" />
                <h3 className="glass-label text-sm tracking-wider">Inference Envelope (Daily Density)</h3>
            </div>

            {loading ? (
                <div className="h-56 flex items-center justify-center text-xs opacity-50 font-mono tracking-widest animate-pulse">
                    COMPILING_USAGE_DENSITY...
                </div>
            ) : data.length === 0 ? (
                <div className="h-56 flex items-center justify-center text-xs opacity-50">
                    No timeline activity recorded yet
                </div>
            ) : (
                <div className="h-56 w-full mt-2">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                            <XAxis
                                dataKey="date"
                                tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.4)' }}
                                axisLine={false}
                                tickLine={false}
                            />
                            <YAxis
                                yAxisId="left"
                                tick={{ fontSize: 10, fill: 'rgba(255,255,255,0.4)' }}
                                axisLine={false}
                                tickLine={false}
                                tickFormatter={(val) => `${(val / 1000).toFixed(0)}k`}
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
                            <Bar
                                yAxisId="left"
                                dataKey="tokens"
                                fill="url(#colorTokens)"
                                radius={[4, 4, 0, 0]}
                                name="Total Tokens"
                            />
                            <defs>
                                <linearGradient id="colorTokens" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#91D65F" stopOpacity={0.8} />
                                    <stop offset="95%" stopColor="#91D65F" stopOpacity={0.2} />
                                </linearGradient>
                            </defs>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}
        </div>
    );
};

export default DailyBarChart;
