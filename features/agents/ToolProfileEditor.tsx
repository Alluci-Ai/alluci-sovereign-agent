import React, { useState, useEffect } from 'react';
import { useStore } from '../../store/useStore';
import { ToggleLeft, ToggleRight, Settings } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

interface ToolProfileEditorProps {
    agentId: string;
}

export const ToolProfileEditor: React.FC<ToolProfileEditorProps> = ({ agentId }) => {
    const { accessToken } = useStore();
    const [tools, setTools] = useState<any[]>([]);

    useEffect(() => {
        const fetchTools = async () => {
            try {
                const res = await fetch(`${DAEMON_URL}/api/v1/agents/${agentId}/tools`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include'
                });
                if (res.ok) {
                    const data = await res.json();

                    setTools(data.tools || []);
                }
            } catch (err) {
                console.error('Failed fetching agent tools', err);
            }
        };
        fetchTools();
    }, [agentId, accessToken]);

    const toggleTool = async (index: number) => {
        const next = [...tools];
        next[index].enabled = !next[index].enabled;
        setTools(next);

        try {
            await fetch(`${DAEMON_URL}/api/v1/agents/${agentId}/tools`, {
                method: 'PUT',
                headers: { 'Authorization': `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ tools: next }),
                credentials: 'include'
            });
        } catch (e) { }
    };

    return (
        <div className="bg-glass-1 border border-glass-edge rounded-xl p-4 flex flex-col gap-4 animate-in fade-in zoom-in-95 duration-300 relative z-20">
            <h3 className="glass-label text-[10px] tracking-widest m-0 px-2 uppercase border-b border-glass-edge pb-2">Enabled Extrinsic Dependencies</h3>

            <div className="flex flex-col gap-3 max-w-3xl">
                {tools.map((t, i) => (
                    <div key={i} className={`p-4 rounded-xl border transition-colors ${t.enabled ? 'border-status-good/30 bg-status-good/5' : 'border-glass-edge bg-glass-2'}`}>
                        <div className="flex items-center justify-between cursor-pointer" onClick={() => toggleTool(i)}>
                            <div>
                                <span className="font-mono text-[13px] text-text-primary tracking-tight">{t.name}</span>
                                <p className="text-[10px] text-text-tertiary mt-1">{t.description}</p>
                            </div>
                            <div className="text-text-primary flex items-center gap-2">
                                <span className={`glass-label text-[9px] ${t.enabled ? 'text-status-good' : 'opacity-40'}`}>{t.enabled ? 'ACTIVE' : 'DORMANT'}</span>
                                {t.enabled ? <ToggleRight size={20} className="text-status-good drop-shadow-[0_0_8px_rgba(48,209,88,0.4)]" /> : <ToggleLeft size={20} className="text-glass-edge" />}
                            </div>
                        </div>

                        {t.enabled && (
                            <div className="mt-4 pt-3 border-t border-glass-edge/40 flex flex-col gap-2">
                                <label className="text-[9px] font-mono uppercase text-accent flex gap-1 items-center"><Settings size={10} /> Parameter Overrides (JSON)</label>
                                <textarea
                                    className="bg-black/40 border border-white/5 p-2 rounded-lg text-[10px] text-blue-200 font-mono resize-none outline-none h-12 overflow-hidden focus:border-accent/40 block"
                                    defaultValue={t.params}
                                    spellCheck="false"
                                    onClick={e => e.stopPropagation()}
                                />
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default ToolProfileEditor;
