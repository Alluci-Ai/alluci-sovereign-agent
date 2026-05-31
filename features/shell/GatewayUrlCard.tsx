// eslint-disable-next-line @typescript-eslint/no-unused-vars
import React, { useState, useEffect } from 'react';
import { useStore } from '../../store/useStore';
import { Network, Save, RefreshCw } from 'lucide-react';

export const GatewayUrlCard: React.FC = () => {
    const { daemonStatus, setAccessToken } = useStore();

    // In a real implementation this binds to a settings context/localStorage overlay natively
    const [daemonUrl, setDaemonUrl] = useState(() => localStorage.getItem('VITE_DAEMON_URL') || import.meta.env.VITE_DAEMON_URL || 'http://127.0.0.1:8000');
    const [authToken, setAuthToken] = useState(() => localStorage.getItem('AUTH_TOKEN') || '');
    const [sessionKey, setSessionKey] = useState(() => localStorage.getItem('SESSION_KEY') || '');

    const [saving, setSaving] = useState(false);

    const handleSave = () => {
        setSaving(true);
        localStorage.setItem('VITE_DAEMON_URL', daemonUrl);
        if (authToken) {
            localStorage.setItem('alluci_access_token', authToken);
            localStorage.setItem('AUTH_TOKEN', authToken);
        }
        if (sessionKey) localStorage.setItem('SESSION_KEY', sessionKey);

        // Push explicitly into Zustand if available or reload window
        setAccessToken(authToken || null);

        setTimeout(() => {
            setSaving(false);
            window.location.reload(); // Hard re-init for socket resets explicitly requested
        }, 300);
    };

    return (
        <div className="bg-glass-1 border border-glass-edge p-5 rounded-xl flex flex-col gap-4 relative animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between border-b border-glass-edge pb-3">
                <h3 className="text-xs font-medium tracking-tight flex items-center gap-2">
                    <Network size={14} className="text-accent" /> Socket Gateway Conduit
                </h3>
                <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase font-mono tracking-widest opacity-60">Status:</span>
                    <span className={`px-2 py-0.5 rounded-full text-[9px] font-mono tracking-wider ${daemonStatus === 'ONLINE' ? 'bg-status-good/10 text-status-good border border-status-good/20' : 'bg-status-error/10 text-status-error border border-status-error/20'}`}>
                        {daemonStatus}
                    </span>
                </div>
            </div>

            <div className="flex flex-col gap-3">
                <div className="flex flex-col gap-1">
                    <label className="text-[10px] text-text-tertiary">Daemon Base URL</label>
                    <input
                        type="text"
                        className="glass-input text-xs font-mono w-full"
                        value={daemonUrl}
                        onChange={e => setDaemonUrl(e.target.value)}
                    />
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="flex flex-col gap-1">
                        <label className="text-[10px] text-text-tertiary">Auth Token</label>
                        <input
                            type="password"
                            className="glass-input text-xs font-mono w-full text-blue-300"
                            placeholder="****************"
                            value={authToken}
                            onChange={e => setAuthToken(e.target.value)}
                        />
                    </div>
                    <div className="flex flex-col gap-1">
                        <label className="text-[10px] text-text-tertiary">Static Session Key (Optional)</label>
                        <input
                            type="text"
                            className="glass-input text-xs font-mono w-full"
                            placeholder="sess_..."
                            value={sessionKey}
                            onChange={e => setSessionKey(e.target.value)}
                        />
                    </div>
                </div>
            </div>

            <div className="flex justify-end pt-2">
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="glass-btn flex items-center gap-2 px-4 shadow-sm"
                    style={{ fontSize: 11, padding: '6px 16px' }}
                >
                    {saving ? <RefreshCw size={12} className="animate-spin" /> : <Save size={12} />}
                    {saving ? 'Re-initializing...' : 'Apply & Restart'}
                </button>
            </div>
        </div>
    );
};

export default GatewayUrlCard;
