import React, { useEffect, useState, useRef } from 'react';
import { useStore } from '../../store/useStore';
import { Terminal, Filter, Download, Pause, Play, Trash2 } from 'lucide-react';

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const DAEMON_WS_URL = import.meta.env.VITE_DAEMON_WS_URL || 'ws://127.0.0.1:8000';

interface LogEntry {
    timestamp: string;
    level: string;
    logger: string;
    message: string;
    session_key?: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    payload?: any;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    [key: string]: any;
}

export const LogPanel: React.FC = () => {
    const { accessToken, theme } = useStore();
    const isDark = theme === 'dark';
    const [logs, setLogs] = useState<LogEntry[]>([]);

    // Filters
    const [levelFilter, setLevelFilter] = useState<string>('ALL');
    const [sessionFilter, setSessionFilter] = useState<string>('');
    const [isPaused, setIsPaused] = useState<boolean>(false);

    // Scrolling
    const [autoScroll, setAutoScroll] = useState<boolean>(true);
    const containerRef = useRef<HTMLDivElement>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const isPausedRef = useRef(isPaused);

    // Sync paused ref for closure payload
    useEffect(() => {
        isPausedRef.current = isPaused;
    }, [isPaused]);

    useEffect(() => {
        const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = import.meta.env.VITE_DAEMON_URL
            ? import.meta.env.VITE_DAEMON_URL.replace(/^http/, 'ws')
            : `${proto}//${window.location.host}`;

        let reconnectTimeout: ReturnType<typeof setTimeout>;

        const connect = () => {
            const ws = new WebSocket(`${host}/api/logs/stream`);
            ws.onopen = () => {
                ws.send(JSON.stringify({ type: 'auth', token: accessToken }));
            };
            ws.onmessage = (event) => {
                if (isPausedRef.current) return;
                try {
                    const parsed = JSON.parse(event.data);
                    setLogs(prev => {
                        const next = [...prev, parsed];
                        // Limit buffer to 2000 lines
                        if (next.length > 2000) return next.slice(next.length - 2000);
                        return next;
                    });
                } catch (err) {
                    console.error('Failed to parse log stream payload', err);
                }
            };
            ws.onclose = () => {
                // Auto-reconnect after 3 seconds
                reconnectTimeout = setTimeout(() => {
                    connect();
                }, 3000);
            };
            wsRef.current = ws;
        };

        connect();

        return () => {
            clearTimeout(reconnectTimeout);
            if (wsRef.current) {
                wsRef.current.onclose = null; // Prevent reconnect on unmount
                wsRef.current.close();
            }
        };
    }, [accessToken]);

    useEffect(() => {
        if (autoScroll && containerRef.current) {
            containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }
    }, [logs, autoScroll]);

    const handleExport = () => {
        const jsonl = logs.map(l => JSON.stringify(l)).join('\n');
        const blob = new Blob([jsonl], { type: 'application/x-ndjson' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `system_logs_${Date.now()}.jsonl`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const handleScroll = () => {
        if (!containerRef.current) return;
        const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
        const isAtBottom = Math.abs(scrollHeight - clientHeight - scrollTop) < 20;
        setAutoScroll(isAtBottom);
    };

    const flushLogs = () => setLogs([]);

    const filteredLogs = logs.filter(l => {
        if (levelFilter !== 'ALL' && (l.level || '').toUpperCase() !== levelFilter) return false;
        if (sessionFilter && !(l.session_key || '').includes(sessionFilter) && !(l.message || '').includes(sessionFilter)) return false;
        return true;
    });

    const getLevelColor = (level: string) => {
        const lvl = (level || '').toUpperCase();
        if (!isDark) {
            // LIGHT MODE: Full-line Greyscale Graduation
            switch (lvl) {
                case 'ERROR': case 'CRITICAL': return 'text-zinc-900 font-extrabold';
                case 'WARNING': case 'WARN': return 'text-zinc-500 font-bold';
                case 'DEBUG': return 'text-zinc-400 font-medium';
                case 'INFO': default: return 'text-black font-normal';
            }
        } else {
            // DARK MODE: Color level differentiation
            switch (lvl) {
                case 'ERROR': case 'CRITICAL': return 'text-tension font-bold';
                case 'WARNING': case 'WARN': return 'text-amber-400 font-bold';
                case 'DEBUG': return 'text-cyan-400 opacity-70 font-medium';
                case 'INFO': default: return 'text-text-primary font-normal';
            }
        }
    };

    return (
        <div className="inline-panel-wrapper overflow-auto">
            <div className="max-w-7xl mx-auto w-full flex flex-col gap-4 lg:p-6 p-4 h-full">

                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <Terminal size={20} className="text-accent" />
                        <h2 className="text-xl font-medium tracking-tight text-text-primary">Daemon Log Stream</h2>
                    </div>

                    <div className="flex items-center gap-3 bg-glass-1 border border-glass-edge rounded-lg px-2 py-1.5 backdrop-blur-md overflow-x-auto text-[11px] glass-label">
                        <div className="flex items-center gap-2 px-2 border-r border-glass-edge pr-4">
                            <Filter size={12} className="text-text-secondary" />
                            <select
                                value={levelFilter}
                                onChange={e => setLevelFilter(e.target.value)}
                                className="bg-transparent border-none text-text-primary focus:outline-none"
                            >
                                <option value="ALL">ALL LEVELS</option>
                                <option value="DEBUG">DEBUG</option>
                                <option value="INFO">INFO</option>
                                <option value="WARNING">WARNING</option>
                                <option value="ERROR">ERROR</option>
                            </select>
                        </div>

                        <div className="px-2 border-r border-glass-edge">
                            <input
                                type="text"
                                placeholder="Filter by Session UUID or exact message..."
                                value={sessionFilter}
                                onChange={e => setSessionFilter(e.target.value)}
                                className="bg-transparent border-none focus:outline-none text-text-primary w-48 placeholder-opacity-40"
                            />
                        </div>

                        <div className="flex items-center gap-1 px-2">
                            <button
                                onClick={() => setIsPaused(!isPaused)}
                                className={`p-1.5 rounded-md transition-colors ${isPaused ? (isDark ? 'bg-amber-500/20 text-amber-500 font-bold' : 'bg-zinc-200 text-black font-bold') : 'hover:bg-glass-edge text-text-secondary hover:text-text-primary'}`}
                                title={isPaused ? "Resume Stream" : "Pause Stream"}
                            >
                                {isPaused ? <Play size={14} /> : <Pause size={14} />}
                            </button>
                            <button
                                onClick={flushLogs}
                                className="p-1.5 rounded-md hover:bg-glass-edge text-text-secondary hover:text-text-primary transition-colors"
                                title="Clear Buffer"
                            >
                                <Trash2 size={14} />
                            </button>
                            <button
                                onClick={handleExport}
                                className="p-1.5 rounded-md hover:bg-glass-edge text-text-secondary hover:text-text-primary transition-colors"
                                title="Export JSONL"
                            >
                                <Download size={14} />
                            </button>
                        </div>
                    </div>
                </div>

                <div
                    ref={containerRef}
                    onScroll={handleScroll}
                    className="flex-1 bg-glass-1 border border-glass-edge rounded-xl p-4 overflow-y-auto font-mono text-[11px] leading-relaxed relative min-h-[500px]"
                >
                    {filteredLogs.length === 0 ? (
                        <div className="absolute inset-0 flex items-center justify-center text-text-tertiary opacity-50 tracking-widest">
                            AWAITING_STREAM_BUFFER...
                        </div>
                    ) : (
                        filteredLogs.map((log, idx) => (
                            <div key={idx} className={`flex gap-3 py-1 hover:bg-glass-hover border-b border-glass-edge transition-colors ${getLevelColor(log.level)}`}>
                                <span className="whitespace-nowrap hidden md:inline font-mono opacity-60">
                                    {(log.timestamp || new Date().toISOString()).split('T')[1]?.slice(0, 12)}
                                </span>
                                <span className="w-16 font-bold flex-shrink-0">{log.level}</span>
                                <span className="w-32 truncate hidden lg:inline flex-shrink-0 opacity-80" title={log.logger}>{log.logger}</span>
                                <span className="flex-1 break-all">{log.message}</span>
                            </div>
                        ))
                    )}
                </div>

                <div className="flex justify-end pr-2 text-[10px] glass-label opacity-60">
                    <span className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${wsRef.current?.readyState === WebSocket.OPEN ? 'bg-status-good shadow-[0_0_8px_var(--status-good-rgb)]' : 'bg-status-error'}`} />
                        {wsRef.current?.readyState === WebSocket.OPEN ? 'STREAM CONNECTED' : 'STREAM DISCONNECTED'}
                        {' '} | {logs.length} Lines Buffered
                    </span>
                </div>
            </div>
        </div>
    );
};

export default LogPanel;
