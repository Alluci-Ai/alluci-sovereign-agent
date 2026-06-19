import React, { useState, useEffect } from 'react';
import { Connection } from '../../../types';
import { SharedModalShell } from './SharedModalShell';
import { activateBridge, saveBridgeCredentials } from '../../../lib/bridgeAuth';
import { useStore } from '../../../store/useStore';
import { adminService } from '../../../adminService';

export const TokenModal: React.FC<{
    connection: Connection;
    onComplete: (session: string, img: string) => void;
    onCancel: () => void;
}> = ({ connection, onComplete, onCancel }) => {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const bridgeId = connection.id;
    const accessToken = useStore(state => state.accessToken);

    // Telegram
    const [tgToken, setTgToken] = useState("");

    // iCloud
    const [appleId, setAppleId] = useState("");
    const [appPassword, setAppPassword] = useState("");
    const [requires2FA, setRequires2FA] = useState(false);
    const [twoFaCode, setTwoFaCode] = useState("");

    // Signal
    const [signalTab, setSignalTab] = useState<'LINK' | 'REGISTER'>('LINK');
    const [signalQr, setSignalQr] = useState<string | null>(null);
    const [signalPhone, setSignalPhone] = useState("");

    useEffect(() => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const handleEvent = (method: string, params: any) => {
            if (method === 'bridge.status' && params.bridge_id === bridgeId) {
                if (params.status === 'CONNECTED') {
                    onComplete(JSON.stringify({ status: 'connected_via_ws' }), "");
                } else if (params.status === '2FA_REQUIRED' && bridgeId === 'icloud') {
                    setRequires2FA(true);
                } else if (params.status === 'QR_READY' && bridgeId === 'sg') {
                    setSignalQr(params.qr_url);
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

            if (bridgeId === 'tg') {
                if (!tgToken) throw new Error("Bot Token is required.");
                creds = { bot_token: tgToken };
            } else if (bridgeId === 'icloud') {
                if (requires2FA) {
                    if (!twoFaCode) throw new Error("2FA Code required.");
                    creds = { apple_id: appleId, app_specific_password: appPassword, two_factor_code: twoFaCode };
                } else {
                    if (!appleId || !appPassword) throw new Error("Apple ID and Password required.");
                    creds = { apple_id: appleId, app_specific_password: appPassword };
                    // Real connection logic will trigger 2FA event if needed
                }
            } else if (bridgeId === 'email') {
                if (!appleId || !appPassword) throw new Error("Email and App-Specific Password required.");
                creds = {
                    email: appleId,
                    password: appPassword,
                    smtp_server: "smtp.mail.me.com",
                    imap_server: "imap.mail.me.com",
                    smtp_port: 587,
                    imap_port: 993
                };
            } else if (bridgeId === 'sg') {
                if (signalTab === 'REGISTER') {
                    if (!signalPhone) throw new Error("Phone number required.");
                    creds = { phone_number: signalPhone, link_type: 'primary' };
                } else {
                    // Link flow - usually backend polls, but we'll simulate success
                    creds = { link_type: 'secondary', linked_at: new Date().toISOString() };
                }
            }

            const saved = await saveBridgeCredentials(bridgeId, creds, accessToken || "");
            if (!saved) throw new Error("Failed to save credentials");

            const activated = await activateBridge(bridgeId, accessToken || "");
            if (activated?.requires_2fa) {
                setRequires2FA(true);
                if (activated.error) {
                    throw new Error(activated.error);
                }
            } else if (!activated?.connected) {
                throw new Error(activated?.error || `Bridge activation failed.`);
            } else {
                onComplete(JSON.stringify(creds), "");
            }
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
                    Connect your <strong>{connection.name}</strong> securely via explicit credentials.
                </p>

                {bridgeId === 'tg' && (
                    <div className="w-full max-w-[280px] flex flex-col gap-3">
                        <div className="flex flex-col gap-1">
                            <label className="text-[10px] text-text-tertiary font-mono">Telegram Bot Token</label>
                            <input
                                type="password"
                                value={tgToken}
                                onChange={e => setTgToken(e.target.value)}
                                placeholder="e.g. 123456:ABC-DEF1234..."
                                className="w-full bg-layer-divider border border-layer-3 rounded px-3 py-2 text-sm text-text-primary outline-none focus:border-layer-4 transition-colors font-mono"
                            />
                            <p className="text-[10px] text-text-tertiary">Create a bot at t.me/BotFather to get a token.</p>
                        </div>
                    </div>
                )}

                {bridgeId === 'icloud' && (
                    <div className="w-full max-w-[280px] flex flex-col gap-3">
                        <div className="flex flex-col gap-1">
                            <label className="text-[10px] text-text-tertiary font-mono">Apple ID Email</label>
                            <input
                                type="email"
                                name="username"
                                autoComplete="username"
                                value={appleId}
                                disabled={requires2FA}
                                onChange={e => setAppleId(e.target.value)}
                                placeholder="name@icloud.com"
                                className="w-full bg-layer-divider border border-layer-3 rounded px-3 py-2 text-sm text-text-primary outline-none disabled:opacity-50 font-mono"
                            />
                        </div>
                        <div className="flex flex-col gap-1">
                            <label className="text-[10px] text-text-tertiary font-mono">Apple ID Password</label>
                            <input
                                type="password"
                                name="password"
                                autoComplete="current-password"
                                value={appPassword}
                                disabled={requires2FA}
                                onChange={e => setAppPassword(e.target.value)}
                                placeholder="Your real Apple ID Password"
                                className="w-full bg-layer-divider border border-layer-3 rounded px-3 py-2 text-sm text-text-primary outline-none disabled:opacity-50 font-mono"
                            />
                            <p className="text-[10px] text-orange-400/80 leading-tight mt-1">App-Specific passwords will NOT work for Drive/Reminders sync. Real password required.</p>
                        </div>

                        {requires2FA && (
                            <div className="flex flex-col gap-1 mt-2 p-3 bg-layer-2 rounded border border-blue-500/30">
                                <label className="text-xs text-blue-400 font-medium font-mono">Apple 2FA Code</label>
                                <input
                                    type="text"
                                    name="one-time-code"
                                    autoComplete="one-time-code"
                                    inputMode="numeric"
                                    pattern="[0-9]*"
                                    value={twoFaCode}
                                    onChange={e => setTwoFaCode(e.target.value)}
                                    placeholder="Enter 6-digit code"
                                    className="w-full bg-layer-divider border border-layer-3 rounded px-3 py-2 text-sm text-text-primary outline-none font-mono tracking-widest text-center"
                                />
                            </div>
                        )}
                    </div>
                )}

                {bridgeId === 'email' && (
                    <div className="w-full max-w-[280px] flex flex-col gap-3">
                        <div className="flex flex-col gap-1">
                            <label className="text-[10px] text-text-tertiary font-mono">Email Address</label>
                            <input
                                type="text"
                                value={appleId}
                                onChange={e => setAppleId(e.target.value)}
                                placeholder="name@icloud.com"
                                className="w-full bg-layer-divider border border-layer-3 rounded px-3 py-2 text-sm text-text-primary outline-none font-mono"
                            />
                        </div>
                        <div className="flex flex-col gap-1">
                            <label className="text-[10px] text-text-tertiary font-mono">App-Specific Password</label>
                            <input
                                type="password"
                                value={appPassword}
                                onChange={e => setAppPassword(e.target.value)}
                                placeholder="xxxx-xxxx-xxxx-xxxx"
                                className="w-full bg-layer-divider border border-layer-3 rounded px-3 py-2 text-sm text-text-primary outline-none font-mono"
                            />
                            <a href="https://appleid.apple.com" target="_blank" rel="noreferrer" className="text-[10px] text-blue-400 hover:underline">Generate at appleid.apple.com → Security</a>
                        </div>
                    </div>
                )}

                {bridgeId === 'sg' && (
                    <div className="w-full max-w-[280px] flex flex-col gap-3">
                        <div className="flex bg-layer-2 rounded p-1 mb-2">
                            <button
                                onClick={() => setSignalTab('LINK')}
                                className={`flex-1 text-xs py-1 rounded transition-colors ${signalTab === 'LINK' ? 'bg-layer-divider text-white' : 'text-text-tertiary hover:text-text-secondary'}`}
                            >Link QR</button>
                            <button
                                onClick={() => setSignalTab('REGISTER')}
                                className={`flex-1 text-xs py-1 rounded transition-colors ${signalTab === 'REGISTER' ? 'bg-layer-divider text-white' : 'text-text-tertiary hover:text-text-secondary'}`}
                            >Register</button>
                        </div>

                        {signalTab === 'LINK' && (
                            <div className="flex flex-col justify-center items-center bg-white p-4 rounded aspect-square w-full">
                                {signalQr ? (
                                    <div className="text-black text-center text-xs">
                                        [ QR Code generated from ]<br /><br />
                                        <span className="font-mono text-[10px] break-all">{signalQr}</span>
                                    </div>
                                ) : (
                                    <div className="text-gray-500 text-sm">Generating QR...</div>
                                )}
                            </div>
                        )}

                        {signalTab === 'REGISTER' && (
                            <div className="flex flex-col gap-1">
                                <label className="text-[10px] text-text-tertiary font-mono">Phone Number (E.164)</label>
                                <input
                                    type="text"
                                    value={signalPhone}
                                    onChange={e => setSignalPhone(e.target.value)}
                                    placeholder="+1234567890"
                                    className="w-full bg-layer-divider border border-layer-3 rounded px-3 py-2 text-sm text-text-primary outline-none focus:border-layer-4 transition-colors font-mono"
                                />
                            </div>
                        )}
                    </div>
                )}

                {error && <p className="text-red-400 text-xs text-center">{error}</p>}

                <button
                    onClick={handleSubmit}
                    disabled={isLoading}
                    className="bg-accent-teal/80 hover:bg-accent-teal text-white font-medium py-2 px-6 rounded-lg transition-colors disabled:opacity-50 w-full max-w-[280px] mt-2"
                >
                    {isLoading ? 'Processing...' : (requires2FA ? 'Submit 2FA' : 'Connect Account')}
                </button>
            </div>
        </SharedModalShell>
    );
};
