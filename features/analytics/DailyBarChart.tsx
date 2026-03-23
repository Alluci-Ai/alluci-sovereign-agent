import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { useStore } from '../../store/useStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://127.0.0.1:8000';

interface DailyBarChartProps {
    startDate?: string;
    endDate?: string;
    mode: 'tokens' | 'cost';
}

export const DailyBarChart: React.FC<DailyBarChartProps> = ({ startDate, endDate, mode }) => {
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

                const res = await fetch(`${DAEMON_URL}/api/v1/usage/daily?${params}`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include',
                });
                if (res.ok) {
                    const series = await res.json();

                    const chartData = series.map((d: any) => {
                        const dateObj = new Date(d.date);
                        // Convert to Local day to avoid UTC shift bug if needed, or stick to UTC string parsing.
                        const tzFormat = new Date(dateObj.getTime() + dateObj.getTimezoneOffset() * 60000);
                        return {
                            date: tzFormat.toLocaleDateString(undefined, { weekday: 'short' }),
                            tokens: d.input_tokens + d.output_tokens + (d.cache_read || 0) + (d.cache_write || 0),
                            cost: d.cost,
                            turns: d.turns,
                            rawDate: d.date
                        }
                    });

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

    if (loading) {
        return (
            <div className="h-64 flex items-center justify-center text-xs opacity-50 font-mono tracking-widest animate-pulse">
                COMPILING_{mode.toUpperCase()}_DENSITY...
            </div>
        );
    }

    if (data.length === 0) {
        return (
            <div className="h-64 flex items-center justify-center text-xs opacity-50">
                No timeline activity recorded yet
            </div>
        );
    }

    const formatYAxis = (val: number) => {
        if (mode === 'tokens') {
            if (val === 0) return '0';
            if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`;
            if (val >= 1000) return `${(val / 1000).toFixed(0)}K`;
            return val.toString();
        } else {
            return `$${val.toFixed(2)}`;
        }
    };

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            const dataPoint = payload[0].payload;
            return (
                <div className="bg-glass-2 border border-glass-edge rounded-lg p-3 backdrop-blur-xl shadow-xl">
                    <p className="text-xs text-text-secondary uppercase mb-1 font-bold tracking-widest">{dataPoint.rawDate}</p>
                    <p className="text-sm text-text-primary">
                        {mode === 'tokens'
                            ? `${dataPoint.tokens.toLocaleString()} Tokens`
                            : `$${dataPoint.cost.toFixed(4)}`}
                    </p>
                </div>
            );
        }
        return null;
    };

    return (
        <div className="h-64 w-full mt-2">
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} margin={{ top: 20, right: 0, left: -20, bottom: 0 }}>
                    <XAxis
                        dataKey="date"
                        tick={{ fontSize: 11, fill: 'rgba(255,255,255,0.4)', fontWeight: 500 }}
                        axisLine={false}
                        tickLine={false}
                        tickMargin={12}
                    />
                    {/* Add label on top of bars to match the screenshot */}
                    <YAxis
                        yAxisId="left"
                        tick={false}
                        axisLine={false}
                        tickLine={false}
                        hide={true} // Hidden Y axis because values are above bars in screenshot
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                    <Bar
                        yAxisId="left"
                        dataKey={mode}
                        radius={[4, 4, 0, 0]}
                        name={mode === 'tokens' ? 'Tokens' : 'Cost'}
                        isAnimationActive={true}
                        label={{
                            position: 'top',
                            formatter: formatYAxis,
                            fill: 'rgba(255,255,255,0.5)',
                            fontSize: 10,
                            fontWeight: 500,
                            dy: -5
                        }}
                    >
                        {data.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill="url(#colorTokens)" />
                        ))}
                    </Bar>
                    <defs>
                        <linearGradient id="colorTokens" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#25a297" stopOpacity={0.9} />
                            <stop offset="100%" stopColor="#4f46e5" stopOpacity={0.7} />
                        </linearGradient>
                    </defs>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
};

export default DailyBarChart;
