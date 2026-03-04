import React, { useState, useEffect, useRef } from 'react';
import { adminService } from '../../adminService';
import { useStore } from '../../store/useStore';
import { Terminal, Send, X, ChevronRight, Activity, Cpu, Layers } from 'lucide-react';

interface MethodSchema {
    description?: string;
    params?: Record<string, string>;
}

export const RpcConsole: React.FC = () => {
    const [methods, setMethods] = useState<Record<string, MethodSchema>>({});
    const [selectedMethod, setSelectedMethod] = useState<string>('');
    const [paramsInput, setParamsInput] = useState<string>('{}');
    const [logs, setLogs] = useState<{ type: 'req' | 'res' | 'err'; content: any; timestamp: string }[]>([]);
    const [isExpanded, setIsExpanded] = useState(false);
    const logEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Fetch methods on mount
        // Hook into system events to capture RPC results for this console
        const handleEvent = (method: string, params: any) => {
            if (method === 'methods.list') {
                setMethods(params.methods || {});
            } else if (method === 'rpc.response') {
                setLogs(prev => [...prev, {
                    type: 'res',
                    content: params.result,
                    timestamp: new Date().toLocaleTimeString()
                }]);
            } else if (method === 'rpc.error') {
                setLogs(prev => [...prev, {
                    type: 'err',
                    content: params.error,
                    timestamp: new Date().toLocaleTimeString()
                }]);
            }
        };

        adminService.addListener(handleEvent);

        // Fetch methods on mount
        adminService.sendRPC('methods.list', {});

        return () => {
            adminService.removeListener(handleEvent);
        };
    }, []);

    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    const handleSend = () => {
        try {
            const parsedParams = JSON.parse(paramsInput);
            const id = adminService.sendRPC(selectedMethod, parsedParams);

            const logEntry = {
                type: 'req' as const,
                content: { method: selectedMethod, params: parsedParams, id },
                timestamp: new Date().toLocaleTimeString()
            };
            setLogs(prev => [...prev, logEntry]);
        } catch (e) {
            setLogs(prev => [...prev, {
                type: 'err',
                content: `Invalid JSON Params: ${e}`,
                timestamp: new Date().toLocaleTimeString()
            }]);
        }
    };

    const clearLogs = () => setLogs([]);

    return (
        <div className={`fixed bottom-6 right-6 z-50 transition-all duration-500 ease-in-out ${isExpanded ? 'w-[500px] h-[600px]' : 'w-14 h-14'}`}>
            {!isExpanded ? (
                <button
                    onClick={() => setIsExpanded(true)}
                    className="w-full h-full rounded-2xl bg-white/10 backdrop-blur-xl border border-white/20 flex items-center justify-center hover:bg-white/20 transition-all shadow-2xl"
                >
                    <Terminal size={24} className="text-white/80" />
                </button>
            ) : (
                <div className="w-full h-full rounded-3xl bg-[#0a0a0c]/80 backdrop-blur-3xl border border-white/10 shadow-[0_20px_50px_rgba(0,0,0,0.5)] flex flex-col overflow-hidden">
                    {/* Header */}
                    <div className="px-5 py-4 border-b border-white/5 flex items-center justify-between bg-white/[0.02]">
                        <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center border border-blue-500/30">
                                <Activity size={16} className="text-blue-400" />
                            </div>
                            <div>
                                <h3 className="text-sm font-semibold text-white">Sovereign RPC Console</h3>
                                <p className="text-[10px] text-white/40 uppercase tracking-widest font-medium">Debug Interface v1.4</p>
                            </div>
                        </div>
                        <button
                            onClick={() => setIsExpanded(false)}
                            className="p-2 hover:bg-white/5 rounded-xl transition-colors text-white/40 hover:text-white"
                        >
                            <X size={18} />
                        </button>
                    </div>

                    {/* Log Area */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-hide">
                        {logs.length === 0 && (
                            <div className="h-full flex flex-col items-center justify-center text-white/20 space-y-2">
                                <Layers size={32} />
                                <span className="text-xs font-medium">No activity recorded</span>
                            </div>
                        )}
                        {logs.map((log, i) => (
                            <div key={i} className={`p-3 rounded-xl border text-xs font-mono break-all ${log.type === 'req' ? 'bg-blue-500/5 border-blue-500/10 text-blue-300' :
                                log.type === 'res' ? 'bg-emerald-500/5 border-emerald-500/10 text-emerald-300' :
                                    'bg-red-500/5 border-red-500/10 text-red-300'
                                }`}>
                                <div className="flex items-center justify-between mb-1 opacity-50 text-[10px]">
                                    <span>{log.type.toUpperCase()}</span>
                                    <span>{log.timestamp}</span>
                                </div>
                                <pre className="whitespace-pre-wrap">{JSON.stringify(log.content, null, 2)}</pre>
                            </div>
                        ))}
                        <div ref={logEndRef} />
                    </div>

                    {/* Footer / Controls */}
                    <div className="p-4 bg-black/40 border-t border-white/5 space-y-3">
                        <div className="flex gap-2">
                            <select
                                value={selectedMethod}
                                onChange={(e) => setSelectedMethod(e.target.value)}
                                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none focus:border-blue-500/50 transition-all appearance-none"
                            >
                                <option value="">Select Method...</option>
                                {Object.keys(methods).sort().map(m => (
                                    <option key={m} value={m}>{m}</option>
                                ))}
                            </select>
                            <button
                                onClick={clearLogs}
                                className="px-3 py-2 text-[10px] font-bold text-white/40 hover:text-white transition-colors uppercase"
                            >
                                Clear
                            </button>
                        </div>

                        {selectedMethod && methods[selectedMethod] && (
                            <div className="px-3 py-2 rounded-lg bg-white/[0.02] border border-white/5">
                                <p className="text-[10px] text-blue-400 font-medium">{methods[selectedMethod].description}</p>
                                {methods[selectedMethod].params && (
                                    <div className="mt-1 flex gap-2">
                                        {Object.entries(methods[selectedMethod].params!).map(([k, v]) => (
                                            <span key={k} className="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-white/30 border border-white/5">
                                                {k}: {v}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}

                        <div className="relative group">
                            <textarea
                                value={paramsInput}
                                onChange={(e) => setParamsInput(e.target.value)}
                                placeholder="JSON-RPC Params..."
                                className="w-full h-24 bg-white/5 border border-white/10 rounded-2xl p-4 text-xs font-mono text-white outline-none focus:border-blue-500/50 transition-all resize-none shadow-inner"
                            />
                            <button
                                onClick={handleSend}
                                disabled={!selectedMethod}
                                className={`absolute bottom-3 right-3 w-10 h-10 rounded-xl flex items-center justify-center transition-all ${selectedMethod ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/40 hover:scale-105 active:scale-95' : 'bg-white/5 text-white/20'
                                    }`}
                            >
                                <Send size={16} />
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
