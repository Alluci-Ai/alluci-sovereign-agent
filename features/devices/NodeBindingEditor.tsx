import React, { useState, useEffect } from 'react';
import { useStore } from '../../store/useStore';
import { Server, Link2, Key, Loader2, AlertCircle } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

interface NodeBindingEditorProps {
    agentId: string;
}

export const NodeBindingEditor: React.FC<NodeBindingEditorProps> = ({ agentId }) => {
    const { accessToken } = useStore();
    const [devices, setDevices] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [bindingState, setBindingState] = useState<Record<string, { loading: boolean, token: string | null }>>({});

    useEffect(() => {
        const fetchDevices = async () => {
            try {
                const res = await fetch(`${DAEMON_URL}/api/devices/status`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include'
                });
                if (res.ok) {
                    const data = await res.json();
                    // For binding UI, we only care about approved devices
                    setDevices(data.devices?.filter((d: any) => d.status === 'approved') || []);
                }
            } catch (err) {
                console.error('Failed fetching device statuses', err);
            } finally {
                setLoading(false);
            }
        };
        fetchDevices();
    }, [accessToken]);

    const handleBind = async (deviceId: number) => {
        setBindingState(prev => ({ ...prev, [deviceId]: { loading: true, token: null } }));
        try {
            const res = await fetch(`${DAEMON_URL}/api/devices/${deviceId}/bind`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
                body: JSON.stringify({ agent_id: agentId }),
                credentials: 'include'
            });
            const data = await res.json();
            if (res.ok) {
                setBindingState(prev => ({ ...prev, [deviceId]: { loading: false, token: data.token } }));
            } else {
                throw new Error(data.detail || 'Binding failed');
            }
        } catch (err: any) {
            alert(`Binding synchronization failed: ${err.message}`);
            setBindingState(prev => ({ ...prev, [deviceId]: { loading: false, token: null } }));
        }
    };

    if (loading) {
        return <div className="animate-pulse h-12 bg-glass-1 rounded-xl border border-glass-edge"></div>;
    }

    return (
        <div className="bg-glass-1 border border-glass-edge rounded-xl p-5 flex flex-col gap-4">
            <h3 className="glass-label text-[10px] tracking-widest text-text-tertiary uppercase flex items-center gap-2 border-b border-glass-edge pb-2 m-0">
                <Server size={12} className="text-accent" /> Node Physical Bindings
            </h3>

            {devices.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-6 text-center gap-2 opacity-50">
                    <AlertCircle size={24} />
                    <span className="text-[11px] font-mono tracking-widest leading-relaxed">NO_APPROVED_HARDWARE_NODES</span>
                </div>
            ) : (
                <div className="flex flex-col gap-3">
                    {devices.map(device => {
                        const state = bindingState[device.id] || { loading: false, token: null };
                        return (
                            <div key={device.id} className="bg-glass-2 border border-white/5 rounded-lg p-3 flex flex-col gap-3 transition-colors hover:border-accent/20">
                                <div className="flex items-center justify-between">
                                    <div className="flex flex-col">
                                        <span className="text-xs font-semibold text-text-primary capitalize">{device.name}</span>
                                        <span className="text-[9px] font-mono text-text-tertiary tracking-wider opacity-70">FP: {device.fingerprint?.slice(0, 16)}...</span>
                                    </div>
                                    <button
                                        onClick={() => handleBind(device.id)}
                                        disabled={state.loading}
                                        className="glass-btn gap-2 shadow-sm" style={{ padding: '4px 12px', fontSize: 10 }}
                                    >
                                        {state.loading ? <Loader2 size={12} className="animate-spin" /> : <Link2 size={12} />}
                                        {state.loading ? 'Rotating...' : 'Rotate Token'}
                                    </button>
                                </div>

                                {state.token && (
                                    <div className="bg-black/60 border border-status-good/30 rounded-md p-2 flex items-center gap-2 animate-in fade-in duration-300">
                                        <Key size={12} className="text-status-good" />
                                        <input
                                            readOnly
                                            value={state.token}
                                            className="bg-transparent text-status-good font-mono text-[10px] w-full outline-none"
                                            onClick={e => (e.target as HTMLInputElement).select()}
                                            title="Active Hardware Binding Token"
                                        />
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
};

export default NodeBindingEditor;
