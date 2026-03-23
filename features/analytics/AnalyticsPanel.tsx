import React, { useEffect, useState } from 'react';
import { useStore } from '../../store/useStore';
import { Calendar, RefreshCw, Globe, Pin, Info, Activity, Database, AlertCircle, Download } from 'lucide-react';
import { DailyBarChart } from './DailyBarChart';
import { SessionsTable } from './SessionsTable';
import { SessionTimeseries } from './SessionTimeseries';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://127.0.0.1:8000';

interface SummaryStats {
    total_input: number;
    total_output: number;
    cache_read: number;
    cache_write: number;
    total_cost: number;
    session_count: number;
    missing_cost_entries?: number;
}

export const AnalyticsPanel: React.FC = () => {
    const { accessToken } = useStore();
    const [startDate, setStartDate] = useState<string>('');
    const [endDate, setEndDate] = useState<string>('');
    const [summary, setSummary] = useState<SummaryStats | null>(null);
    const [sessions, setSessions] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);

    // UI state
    const [isPinned, setIsPinned] = useState(false);
    const [isUTC, setIsUTC] = useState(false);
    const [chartMode, setChartMode] = useState<'tokens' | 'cost'>('tokens');

    // Query / Filter state
    const [query, setQuery] = useState('');

    const fetchData = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (startDate) params.append('start', startDate);
            if (endDate) params.append('end', endDate);

            // Fetch summary
            const sumRes = await fetch(`${DAEMON_URL}/api/v1/usage/summary?${params}`, {
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include',
            });
            if (sumRes.ok) setSummary(await sumRes.json());

            // Fetch sessions
            const sesRes = await fetch(`${DAEMON_URL}/api/v1/usage/sessions?${params}&limit=1000`, {
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include',
            });
            if (sesRes.ok) {
                const payload = await sesRes.json();
                setSessions(payload.sessions || []);
            }
        } catch (err) {
            console.error('[Usage] Failed to fetch manifold data:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [startDate, endDate, accessToken]);

    const formatTokens = (num: number) => {
        if (!num) return '0';
        if (num > 1000000) return (num / 1000000).toFixed(2) + 'M';
        if (num > 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    };

    const formatCost = (num: number) => {
        return `$${num.toFixed(2)}`;
    };

    const totalTokens = summary ? (summary.total_input + summary.total_output + summary.cache_read + summary.cache_write) : 0;

    return (
        <div className="w-full h-full overflow-y-auto overflow-x-hidden relative flex flex-col bg-obsidian text-text-primary">

            {/* Header (Optionally Pinned) */}
            <div className={`w-full z-10 p-6 pb-2 transition-all ${isPinned ? 'sticky top-0 bg-glass-1 backdrop-blur-xl border-b border-glass-edge' : ''}`}>
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 max-w-7xl mx-auto">
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight">Usage</h1>
                        <p className="text-sm text-text-secondary mt-1 tracking-wide">Monitor API usage and costs.</p>
                    </div>

                    <div className="flex items-center gap-2 flex-wrap">
                        {/* Date Controls */}
                        <div className="flex items-center bg-glass-2 border border-glass-edge rounded-lg px-2 py-1">
                            <Calendar size={14} className="text-text-secondary mr-2" />
                            <input
                                type="date"
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                                className="bg-transparent border-none text-xs text-text-primary focus:outline-none w-28"
                            />
                            <span className="text-text-secondary mx-1">→</span>
                            <input
                                type="date"
                                value={endDate}
                                onChange={(e) => setEndDate(e.target.value)}
                                className="bg-transparent border-none text-xs text-text-primary focus:outline-none w-28"
                            />
                        </div>

                        <button onClick={fetchData} className="p-2 rounded-lg bg-glass-2 border border-glass-edge hover:bg-glass-3 transition-colors" title="Refresh">
                            <RefreshCw size={14} className={loading ? 'animate-spin text-accent' : 'text-text-primary'} />
                        </button>
                        <button onClick={() => setIsUTC(!isUTC)} className={`p-2 rounded-lg border transition-colors ${isUTC ? 'bg-accent/20 border-accent text-accent' : 'bg-glass-2 border-glass-edge text-text-primary'}`} title="Toggle Timezone (Local/UTC)">
                            <Globe size={14} />
                        </button>
                        <button onClick={() => setIsPinned(!isPinned)} className={`p-2 rounded-lg border transition-colors ${isPinned ? 'bg-accent/20 border-accent text-accent' : 'bg-glass-2 border-glass-edge text-text-primary'}`} title="Pin Header">
                            <Pin size={14} />
                        </button>
                    </div>
                </div>
            </div>

            <div className="flex-1 max-w-7xl mx-auto w-full p-6 flex flex-col gap-6">

                {/* Summary Stat Row */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="bg-glass-1 border border-glass-edge rounded-xl p-5 relative overflow-hidden flex flex-col justify-between h-32">
                        <div className="text-xs font-semibold tracking-wider text-text-secondary uppercase">Total Tokens</div>
                        <div className="text-4xl font-light text-indigo-400 mt-2 tracking-tight">{formatTokens(totalTokens)}</div>
                        <div className="text-xs text-text-secondary mt-auto">This period</div>

                        {/* Compact Cost Breakdown inside Token tile or near it */}
                        <div className="absolute bottom-0 left-0 right-0 h-1 flex">
                            {summary?.total_input ? <div className="bg-blue-400 h-full" style={{ width: `${(summary.total_input / totalTokens) * 100}%` }} title="Input" /> : null}
                            {summary?.total_output ? <div className="bg-purple-400 h-full" style={{ width: `${(summary.total_output / totalTokens) * 100}%` }} title="Output" /> : null}
                            {summary?.cache_read ? <div className="bg-green-400 h-full" style={{ width: `${(summary.cache_read / totalTokens) * 100}%` }} title="Cache Read" /> : null}
                            {summary?.cache_write ? <div className="bg-orange-400 h-full" style={{ width: `${(summary.cache_write / totalTokens) * 100}%` }} title="Cache Write" /> : null}
                        </div>
                    </div>

                    <div className="bg-glass-1 border border-glass-edge rounded-xl p-5 h-32 flex flex-col justify-between">
                        <div className="text-xs font-semibold tracking-wider text-text-secondary uppercase">Total Cost</div>
                        <div className="text-4xl font-light text-rose-400 mt-2 tracking-tight">{formatCost(summary?.total_cost || 0)}</div>
                        <div className="text-xs text-text-secondary mt-auto">This period</div>
                    </div>

                    <div className="bg-glass-1 border border-glass-edge rounded-xl p-5 h-32 flex flex-col justify-between">
                        <div className="text-xs font-semibold tracking-wider text-text-secondary uppercase">Sessions</div>
                        <div className="text-4xl font-light text-emerald-400 mt-2 tracking-tight">{summary?.session_count || 0}</div>
                        <div className="text-xs text-text-secondary mt-auto">This period</div>
                    </div>
                </div>

                {/* Missing Cost Warnings */}
                {summary?.missing_cost_entries && summary.missing_cost_entries > 0 ? (
                    <div className="bg-amber-900/20 border border-amber-500/30 text-amber-200 px-4 py-3 rounded-xl flex items-center gap-3 text-sm">
                        <AlertCircle size={16} />
                        Missing cost entries for {summary.missing_cost_entries} models. Cost totals may be inaccurate.
                    </div>
                ) : null}

                {/* Daily Bar Chart Container */}
                <div className="bg-glass-1 border border-glass-edge rounded-xl p-6">
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
                        <div>
                            <h2 className="text-lg font-medium">Daily {chartMode === 'tokens' ? 'Token' : 'Cost'} Usage</h2>
                            <p className="text-xs text-text-secondary mt-1 tracking-wide">{chartMode === 'tokens' ? 'Tokens consumed' : 'Costs incurred'} per day this period.</p>
                        </div>
                        <div className="flex items-center rounded-lg border border-glass-edge p-1 bg-glass-2">
                            <button
                                onClick={() => setChartMode('tokens')}
                                className={`px-4 py-1.5 text-xs rounded-md transition-all ${chartMode === 'tokens' ? 'bg-indigo-600/30 border border-indigo-500/30 text-indigo-300' : 'text-text-secondary hover:text-text-primary'}`}
                            >
                                Tokens
                            </button>
                            <button
                                onClick={() => setChartMode('cost')}
                                className={`px-4 py-1.5 text-xs rounded-md transition-all ${chartMode === 'cost' ? 'bg-rose-600/30 border border-rose-500/30 text-rose-300' : 'text-text-secondary hover:text-text-primary'}`}
                            >
                                Cost
                            </button>
                        </div>
                    </div>
                    <DailyBarChart startDate={startDate} endDate={endDate} mode={chartMode} />
                </div>

                {/* Sessions Table Container */}
                <div className="bg-glass-1 border border-glass-edge rounded-xl p-6 mb-12">
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
                        <div>
                            <h2 className="text-lg font-medium">Sessions</h2>
                            <p className="text-xs text-text-secondary mt-1 tracking-wide">Filter and inspect individual sessions.</p>
                        </div>

                        <div className="flex items-center gap-3">
                            <div className="w-64">
                                <input
                                    type="text"
                                    placeholder="Search sessions..."
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    className="w-full bg-glass-2 border border-glass-edge rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-accent transition-colors"
                                />
                            </div>
                            <button
                                className="px-3 py-1.5 text-sm bg-glass-2 hover:bg-glass-3 border border-glass-edge rounded-lg transition-colors flex items-center gap-2"
                                onClick={() => {
                                    window.open(`${DAEMON_URL}/api/v1/usage/sessions/export/csv?start=${startDate}&end=${endDate}&token=${accessToken}`, '_blank');
                                }}
                            >
                                <span>Export CSV</span>
                            </button>
                        </div>
                    </div>

                    <SessionsTable sessions={sessions} query={query} />
                </div>

            </div>
        </div>
    );
};

export default AnalyticsPanel;
