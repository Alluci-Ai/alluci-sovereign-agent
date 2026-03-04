import React, { useEffect, useState } from 'react';
import { useStore } from '../../store/useStore';
import { Calendar, Hash, Coins, Network, ChevronLeft, Activity } from 'lucide-react';
import { TokenFilterBar, TokenFilterState } from './TokenFilterBar';
import { SessionsTable } from './SessionsTable';
import { DailyBarChart } from './DailyBarChart';
import { SessionTimeseries } from './SessionTimeseries';
import { CsvExportButton } from './CsvExportButton';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

interface SummaryStats {
    total_input: number;
    total_output: number;
    total_cost: number;
    session_count: number;
}

export const AnalyticsPanel: React.FC = () => {
    const { accessToken } = useStore();
    const [startDate, setStartDate] = useState<string>('');
    const [endDate, setEndDate] = useState<string>('');
    const [summary, setSummary] = useState<SummaryStats | null>(null);
    const [sessions, setSessions] = useState<any[]>([]);
    const [loadingSessions, setLoadingSessions] = useState(false);

    // Filter State
    const [filters, setFilters] = useState<TokenFilterState>({ query: '' });

    // Selected Session State for Timeseries Detail View Drill-down
    const [selectedSessionKey, setSelectedSessionKey] = useState<string | null>(null);

    useEffect(() => {
        const fetchSummary = async () => {
            try {
                const params = new URLSearchParams();
                if (startDate) params.append('start', startDate);
                if (endDate) params.append('end', endDate);

                const res = await fetch(`${DAEMON_URL}/api/usage/summary?${params}`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include',
                });
                if (res.ok) {
                    setSummary(await res.json());
                }
            } catch (err) {
                console.error('[AnalyticsPanel] Failed to sync usage summary:', err);
            }
        };

        const fetchSessionsData = async () => {
            setLoadingSessions(true);
            try {
                const params = new URLSearchParams();
                if (startDate) params.append('start', startDate);
                if (endDate) params.append('end', endDate);

                const res = await fetch(`${DAEMON_URL}/api/usage/sessions?${params}&limit=500`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include',
                });
                if (res.ok) {
                    const payload = await res.json();
                    setSessions(payload.sessions || []);
                }
            } catch (err) {
                console.error('[AnalyticsPanel] Failed parsing granular sessions layer:', err);
            } finally {
                setLoadingSessions(false);
            }
        };

        fetchSummary();
        fetchSessionsData();
    }, [startDate, endDate, accessToken]);

    // Client-side filtering logic matching the Gap Analysis spec
    const filteredSessions = sessions.filter(s => {
        if (filters.query && !s.session_key.toLowerCase().includes(filters.query.toLowerCase())) return false;
        if (filters.model && !s.models.includes(filters.model)) return false;
        if (filters.minTokens && (s.total_input + s.total_output) < filters.minTokens) return false;
        return true;
    });

    return (
        <div className="inline-panel-wrapper overflow-auto">
            <div className="max-w-7xl mx-auto w-full flex flex-col gap-6 lg:p-6 p-4">

                {/* Header & Date Configuration */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <h2 className="text-xl font-medium tracking-tight text-text-primary">Usage Analytics</h2>

                    <div className="flex items-center gap-3 bg-glass-1 border border-glass-edge rounded-lg px-3 py-2 backdrop-blur-md">
                        <Calendar size={14} className="text-text-secondary" />
                        <input
                            type="date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            className="bg-transparent border-none text-[11px] glass-label text-text-primary focus:outline-none"
                        />
                        <span className="text-text-tertiary opacity-50 px-1">—</span>
                        <input
                            type="date"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                            className="bg-transparent border-none text-[11px] glass-label text-text-primary focus:outline-none"
                        />
                    </div>
                </div>

                {/* KPI Core Envelope Summary Bar */}
                {summary && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <div className="bg-glass-1 border border-glass-edge rounded-xl p-5 flex flex-col gap-2 relative overflow-hidden">
                            <Network className="absolute -right-2 -bottom-2 opacity-[0.03] text-accent" size={80} />
                            <span className="glass-label text-[10px] text-text-tertiary uppercase tracking-wider">Total Active Sessions</span>
                            <span className="text-2xl font-mono text-text-primary tracking-tighter">{summary.session_count.toLocaleString()}</span>
                        </div>

                        <div className="bg-glass-1 border border-glass-edge rounded-xl p-5 flex flex-col gap-2 relative overflow-hidden">
                            <Hash className="absolute -right-2 -bottom-2 opacity-[0.03] text-accent" size={80} />
                            <span className="glass-label text-[10px] text-text-tertiary uppercase tracking-wider">Total Processed Tokens</span>
                            <span className="text-2xl font-mono text-text-primary tracking-tighter">
                                {(summary.total_input + summary.total_output).toLocaleString()}
                            </span>
                        </div>

                        <div className="bg-glass-1 border border-glass-edge rounded-xl p-5 flex flex-col gap-2 relative overflow-hidden">
                            <Coins className="absolute -right-2 -bottom-2 opacity-[0.03] text-status-good" size={80} />
                            <span className="glass-label text-[10px] text-text-tertiary uppercase tracking-wider">Overall Dollar Equivalent Cost</span>
                            <span className="text-2xl font-mono text-status-good tracking-tighter shadow-sm blur-none">
                                ${summary.total_cost.toFixed(4)}
                            </span>
                        </div>

                        <div className="bg-glass-1 border border-glass-edge rounded-xl p-5 flex flex-col gap-2 relative overflow-hidden">
                            <Activity className="absolute -right-2 -bottom-2 opacity-[0.03] text-accent" size={80} />
                            <span className="glass-label text-[10px] text-text-tertiary uppercase tracking-wider">Avg Tokens / Session</span>
                            <span className="text-2xl font-mono text-text-primary tracking-tighter">
                                {summary.session_count > 0
                                    ? Math.round((summary.total_input + summary.total_output) / summary.session_count).toLocaleString()
                                    : '0'}
                            </span>
                        </div>
                    </div>
                )}

                {/* Sub-Layout Structure */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Left Timeline Panel */}
                    <div className="col-span-1 lg:col-span-3">
                        <DailyBarChart startDate={startDate} endDate={endDate} />
                    </div>
                </div>

                {/* Session Breakdown Section */}
                <div className="flex flex-col gap-4 mt-4">

                    {selectedSessionKey ? (
                        <div className="animate-in slide-in-from-right-8 fade-in duration-300">
                            <div className="flex items-center gap-4 mb-4">
                                <button
                                    onClick={() => setSelectedSessionKey(null)}
                                    className="p-2 bg-glass-pressed rounded-full hover:bg-glass-hover transition-colors"
                                >
                                    <ChevronLeft size={16} />
                                </button>
                                <h3 className="text-md text-text-primary">Inspecting Runtime Session Trace</h3>
                            </div>
                            <SessionTimeseries sessionKey={selectedSessionKey} />
                        </div>
                    ) : (
                        <div className="flex flex-col gap-4 animate-in fade-in duration-500">
                            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <TokenFilterBar onFilterChange={setFilters} />
                                <CsvExportButton data={filteredSessions} />
                            </div>
                            <SessionsTable
                                sessions={filteredSessions}
                                loading={loadingSessions}
                                onRowClick={(key) => setSelectedSessionKey(key)}
                            />
                        </div>
                    )}

                </div>
            </div>
        </div>
    );
};

export default AnalyticsPanel;
