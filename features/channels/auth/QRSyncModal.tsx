import React, { useState, useEffect } from 'react';
import { Connection } from '../../../types';
import { SharedModalShell } from './SharedModalShell';
import { activateBridge, saveBridgeCredentials } from '../../../lib/bridgeAuth';
import { useStore } from '../../../store/useStore';
import { adminService } from '../../../adminService';
const DAEMON_URL = import.meta.env.VITE_DAEMON_URL ?? 'http://127.0.0.1:8000';

export const QRSyncModal: React.FC<{
    connection: Connection;
    onComplete: (session: string, img: string) => void;
    onCancel: () => void;
}> = ({ connection, onComplete, onCancel }) => {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const bridgeId = connection.id;
    const accessToken = useStore(state => state.accessToken);

    // WeChat specific
    const [wechatAppId, setWechatAppId] = useState("");
    const [wechatAppSecret, setWechatAppSecret] = useState("");
    const [wechatQr, setWechatQr] = useState<string | null>(null);

    // WhatsApp specific
    const [waMode, setWaMode] = useState<'CLOUD' | 'QR'>('CLOUD');
    const [waPhoneId, setWaPhoneId] = useState("");
    const [waToken, setWaToken] = useState("");

    const handleWechatInit = async () => {
        setIsLoading(true);
        setError(null);
        try {
            if (!wechatAppId || !wechatAppSecret) throw new Error("Open Platform credentials required.");
            // Calls real backend endpoint now
            const res = await fetch(`${useStore.getState().accessToken ? DAEMON_URL : ''}/api/channels/wechat/qr-init`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ app_id: wechatAppId, app_secret: wechatAppSecret })
            });
            if (!res.ok) throw new Error(await res.text());
            const data = await res.json();
            if (data.qr_url) setWechatQr(data.qr_url);
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } catch (e: any) {
            setError(e.message);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const handleEvent = (method: string, params: any) => {
            if (method === 'bridge.status' && params.bridge_id === bridgeId) {
                if (params.status === 'CONNECTED') {
                    onComplete(JSON.stringify({ status: 'connected_via_ws' }), "");
                } else if (params.status === 'QR_READY' && bridgeId === 'wechat') {
                    setWechatQr(params.qr_url);
                }
            }
        };
        adminService.addListener(handleEvent);
        return () => adminService.removeListener(handleEvent);
    }, [bridgeId, onComplete]);

    const handleSubmit = async () => {
        setIsLoading(true);
        setError(null);
        try {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            let creds: Record<string, any> = {};

            if (bridgeId === 'wa') {
                if (waMode === 'CLOUD') {
                    if (!waPhoneId || !waToken) throw new Error("Cloud API fields required.");
                    creds = { phone_number_id: waPhoneId, access_token: waToken, session_type: 'cloud' };
                } else {
                    creds = { session_type: 'qr' };
                }
            } else if (bridgeId === 'wechat') {
                if (!wechatQr) {
                    await handleWechatInit();
                    return;
                }
                creds = { app_id: wechatAppId, app_secret: wechatAppSecret };
            }

            const saved = await saveBridgeCredentials(bridgeId, creds, accessToken || "");
            if (!saved) throw new Error("Failed to save credentials");

            const activated = await activateBridge(bridgeId, accessToken || "");
            if (!activated?.connected) throw new Error(`Bridge activation failed.`);

            onComplete(JSON.stringify(creds), "");
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } catch (e: any) {
            setError(e.message || "Activation Failed");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <SharedModalShell connection={connection} onCancel={onCancel}>
            <div className="flex flex-col gap-4 text-white p-4 items-center">
                <p className="text-text-secondary text-sm text-center mb-2">
                    Synchronize your <strong>{connection.name}</strong> app via QR scan or Cloud API.
                </p>

                {bridgeId === 'wa' && (
                    <div className="w-full max-w-[280px] flex flex-col gap-3">
                        <div className="flex bg-layer-2 rounded p-1 mb-2">
                            <button
                                onClick={() => setWaMode('CLOUD')}
                                className={`flex-1 text-xs py-1 rounded transition-colors ${waMode === 'CLOUD' ? 'bg-layer-divider text-white' : 'text-text-tertiary hover:text-text-secondary'}`}
                            >Cloud API</button>
                            <button
                                onClick={() => setWaMode('QR')}
                                className={`flex-1 text-xs py-1 rounded transition-colors ${waMode === 'QR' ? 'bg-layer-divider text-white' : 'text-text-tertiary hover:text-text-secondary'}`}
                            >Web QR</button>
                        </div>

                        {waMode === 'CLOUD' && (
                            <>
                                <div className="flex flex-col gap-1">
                                    <label className="text-[10px] text-text-tertiary font-mono">Phone Number ID</label>
                                    <input
                                        type="text"
                                        value={waPhoneId}
                                        onChange={e => setWaPhoneId(e.target.value)}
                                        className="w-full bg-layer-divider border border-layer-3 rounded px-3 py-2 text-sm text-text-primary outline-none font-mono"
                                    />
                                </div>
                                <div className="flex flex-col gap-1">
                                    <label className="text-[10px] text-text-tertiary font-mono">System User Access Token</label>
                                    <input
                                        type="password"
                                        value={waToken}
                                        onChange={e => setWaToken(e.target.value)}
                                        className="w-full bg-layer-divider border border-layer-3 rounded px-3 py-2 text-sm text-text-primary outline-none font-mono"
                                    />
                                    <p className="text-[10px] text-text-tertiary mt-1">Found in Meta Business Manager Setup.</p>
                                </div>
                            </>
                        )}

                        {waMode === 'QR' && (
                            <div className="flex flex-col justify-center items-center bg-white p-4 rounded w-full aspect-square">
                                <div className="text-gray-500 text-sm mb-2 font-medium">QR Synchronizer</div>
                                <div className="text-[10px] text-gray-400 text-center">Open WhatsApp on your phone<br />Settings → Linked Devices</div>
                            </div>
                        )}
                    </div>
                )}

                {bridgeId === 'wechat' && (
                    <div className="w-full max-w-[280px] flex flex-col gap-3">
                        {!wechatQr ? (
                            <>
                                <p className="text-xs text-text-tertiary text-center mb-2">WeChat requires Open Platform developer credentials to generate a login QR.</p>
                                <div className="flex flex-col gap-1">
                                    <label className="text-[10px] text-text-tertiary font-mono">App ID</label>
                                    <input
                                        type="text"
                                        value={wechatAppId}
                                        onChange={e => setWechatAppId(e.target.value)}
                                        className="w-full bg-layer-divider border border-layer-3 rounded px-3 py-2 text-sm text-text-primary outline-none font-mono"
                                    />
                                </div>
                                <div className="flex flex-col gap-1">
                                    <label className="text-[10px] text-text-tertiary font-mono">App Secret</label>
                                    <input
                                        type="password"
                                        value={wechatAppSecret}
                                        onChange={e => setWechatAppSecret(e.target.value)}
                                        className="w-full bg-layer-divider border border-layer-3 rounded px-3 py-2 text-sm text-text-primary outline-none font-mono"
                                    />
                                </div>
                            </>
                        ) : (
                            <div className="flex flex-col items-center">
                                <div className="bg-white p-4 rounded mb-2 w-full aspect-square flex items-center justify-center">
                                    <div className="text-black text-xs font-mono break-all text-center">{wechatQr}</div>
                                </div>
                                <p className="text-xs text-text-tertiary">Scan with WeChat to authorize.</p>
                            </div>
                        )}
                    </div>
                )}

                {error && <p className="text-red-400 text-xs text-center">{error}</p>}

                <button
                    onClick={handleSubmit}
                    disabled={isLoading}
                    className="bg-green-600/80 hover:bg-green-600 text-white font-medium py-2 px-6 rounded-lg transition-colors disabled:opacity-50 w-full max-w-[280px] mt-2"
                >
                    {isLoading ? 'Processing...' : (bridgeId === 'wechat' && !wechatQr ? 'Generate QR' : 'Bind Session')}
                </button>
            </div>
        </SharedModalShell>
    );
};
