import React, { useEffect, useState } from 'react';
import { useStore } from '../../store/useStore';
import { adminService } from '../../adminService';
import { Settings2, Save } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://127.0.0.1:8000';

/**
 * SessionOverrides — Panel component allowing users to modify runtime
 * inference parameters bounds explicitly bound to the curren active session footprint.
 */
export const SessionOverrides: React.FC = () => {
    const { activeSessionKey, accessToken } = useStore();
    const [modelOverride, setModelOverride] = useState<string>('auto');
    const [thinkingLevel, setThinkingLevel] = useState<string>('MEDIUM');
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        // Fetch current overrides when active session loads
        const loadConfig = async () => {
            try {
                const res = await fetch(`${DAEMON_URL}/api/v1/sessions/${activeSessionKey}/config`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include',
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.model_override) setModelOverride(data.model_override);
                    if (data.thinking_level) setThinkingLevel(data.thinking_level);
                }
            } catch (err) {
                console.error('[SessionOverrides] Failed loading config:', err);
            }
        };
        loadConfig();
    }, [activeSessionKey, accessToken]);

    const handleSave = () => {
        setIsSaving(true);
        // Dispatch explicit session parameter hot-patch via WS RPC Admin gateway
        adminService.sendRPC('sessions.patch', {
            session_key: activeSessionKey,
            model_override: modelOverride === 'auto' ? null : modelOverride,
            thinking_level: thinkingLevel
        });

        // Optimistic UX feedback delay
        setTimeout(() => setIsSaving(false), 800);
    };

    return (
        <div className="bg-glass-1 border border-glass-edge rounded-xl p-4 flex flex-col gap-4">
            <div className="flex items-center gap-2 mb-2">
                <Settings2 size={16} className="text-accent" />
                <h3 className="glass-label text-xs tracking-wider">Session Constraints</h3>
            </div>

            <div className="flex flex-col gap-2">
                <label className="text-[10px] glass-label text-text-secondary">Force Model Target</label>
                <select
                    value={modelOverride}
                    onChange={e => setModelOverride(e.target.value)}
                    className="glass-input text-xs w-full"
                >
                    <option value="auto">Auto (Router Handled)</option>
                    <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
                    <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                    <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
                    <option value="gpt-4o">GPT-4o</option>
                    <option value="deepseek-reasoner">DeepSeek R1</option>
                </select>
            </div>

            <div className="flex flex-col gap-2">
                <label className="text-[10px] glass-label flex justify-between">
                    <span className="text-text-secondary">Thinking Depth Envelope</span>
                    <span className="text-accent">{thinkingLevel}</span>
                </label>
                <input
                    type="range"
                    min="0" max="2" step="1"
                    value={thinkingLevel === 'LOW' ? 0 : thinkingLevel === 'HIGH' ? 2 : 1}
                    onChange={(e) => {
                        const val = parseInt(e.target.value);
                        setThinkingLevel(val === 0 ? 'LOW' : val === 2 ? 'HIGH' : 'MEDIUM');
                    }}
                    className="w-full accent-accent"
                />
                <div className="flex justify-between text-[8px] glass-label text-text-tertiary">
                    <span>Fast</span><span>Balanced</span><span>Analytical</span>
                </div>
            </div>

            <button
                onClick={handleSave}
                disabled={isSaving}
                className="glass-btn mt-2 flex justify-center gap-2 py-2"
            >
                {isSaving ? <span className="animate-pulse">Syncing Manifold...</span> : <><Save size={14} /> Commit Overrides</>}
            </button>
        </div>
    );
};

export default SessionOverrides;
