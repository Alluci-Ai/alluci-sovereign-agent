// eslint-disable-next-line @typescript-eslint/no-unused-vars
import React, { useState, useEffect } from 'react';
import { Connection } from '../../../types';
import { SharedModalShell } from './SharedModalShell';
import { activateBridge, saveBridgeCredentials } from '../../../lib/bridgeAuth';
import { useStore } from '../../../store/useStore';

export const OAuthModal: React.FC<{
    connection: Connection;
    onComplete: (session: string, img: string) => void;
    onCancel: () => void;
}> = ({ connection, onComplete, onCancel }) => {
    const [step, setStep] = useState<1 | 2>(1);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Discord specific state
    const [discordBotToken, setDiscordBotToken] = useState("");
    const [discordGuildId, setDiscordGuildId] = useState("");

    const [igAccountType, setIgAccountType] = useState<"PERSONAL" | "BUSINESS">("PERSONAL");

    const bridgeId = connection.id;
    const accessToken = useStore(state => state.accessToken);

    const handleOAuthFlow = async () => {
        setIsLoading(true);
        setError(null);
        try {
            // Get proper auth URL from backend
            const res = await fetch(`/api/oauth/${bridgeId}/authorize`);
            if (!res.ok) throw new Error("Failed to initialize OAuth flow");
            const data = await res.json();

            // Open central popup
            const width = 600;
            const height = 700;
            const left = window.screenX + (window.outerWidth - width) / 2;
            const top = window.screenY + (window.outerHeight - height) / 2;
            const popup = window.open(data.authorize_url, 'OAuth', `width=${width},height=${height},left=${left},top=${top}`);

            if (!popup) {
                throw new Error("Popup blocked. Please allow popups for this site.");
            }

            // Monitor for callback via postMessage
            const handleMessage = (event: MessageEvent) => {
                // Ensure same origin
                if (event.origin !== window.location.origin) return;

                if (event.data?.type === 'OAUTH_COMPLETE' && event.data?.bridgeId === bridgeId) {
                    window.removeEventListener('message', handleMessage);

                    if (event.data.error) {
                        setError(event.data.error);
                        setIsLoading(false);
                        return;
                    }

                    if (bridgeId === 'dc') {
                        setStep(2);
                        setIsLoading(false);
                    } else {
                        handleActivation({});
                    }
                }
            };

            window.addEventListener('message', handleMessage);

            // Fallback interval to catch popup closure
            const timer = setInterval(() => {
                if (popup.closed) {
                    clearInterval(timer);
                    setIsLoading(false);
                    window.removeEventListener('message', handleMessage);
                }
            }, 500);

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } catch (e: any) {
            setError(e.message || 'OAuth flow failed');
            setIsLoading(false);
        }
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const handleActivation = async (extraCreds: Record<string, any>) => {
        setIsLoading(true);
        setError(null);
        try {
            const credMap = {
                ...extraCreds,
                ...(bridgeId === 'ig' ? { account_type: igAccountType } : {})
            };

            const saved = await saveBridgeCredentials(bridgeId, credMap, accessToken || "");
            if (!saved) throw new Error("Failed to save credentials");

            const activated = await activateBridge(bridgeId, accessToken || "");
            if (!activated?.connected) throw new Error(`Bridge activation failed for ${bridgeId}`);

            onComplete(JSON.stringify(credMap), "");
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } catch (e: any) {
            setError(e.message || "Activation Failed");
        } finally {
            setIsLoading(false);
        }
    };

    const handleDiscordPhase2 = () => {
        if (!discordBotToken) {
            setError("Bot Token is required.");
            return;
        }
        handleActivation({
            bot_token: discordBotToken,
            guild_id: discordGuildId,
        });
    };

    return (
        <SharedModalShell connection={connection} onCancel={onCancel}>
            <div className="flex flex-col gap-4 text-white p-4">

                {step === 1 && (
                    <div className="flex flex-col items-center gap-4">
                        <p className="text-text-secondary text-center text-sm">
                            Connect your <strong>{connection.name}</strong> account to the Sovereign Agent securely.
                        </p>

                        {bridgeId === 'ig' && (
                            <div className="flex flex-col gap-2 w-full max-w-[250px] mb-2">
                                <label className="text-xs text-text-tertiary">Account Type</label>
                                <select
                                    className="bg-layer-2 border border-layer-3 rounded px-3 py-2 text-sm outline-none w-full"
                                    value={igAccountType}
                                    // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                    onChange={(e) => setIgAccountType(e.target.value as any)}
                                >
                                    <option value="PERSONAL">Personal (Profile Only)</option>
                                    <option value="BUSINESS">Business / Creator (Full DMs)</option>
                                </select>
                                {igAccountType === 'PERSONAL' && (
                                    <div className="text-[10px] text-orange-400 bg-orange-400/10 p-2 rounded mt-1">
                                        Warning: Direct Messages are not accessible via API for Personal accounts. The Agent will only be able to view profile data.
                                    </div>
                                )}
                            </div>
                        )}

                        <button
                            onClick={handleOAuthFlow}
                            disabled={isLoading}
                            className="bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 px-6 rounded-lg transition-colors disabled:opacity-50 w-full max-w-[250px]"
                        >
                            {isLoading ? 'Connecting...' : `Authorize ${connection.name}`}
                        </button>

                        {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
                    </div>
                )}

                {step === 2 && bridgeId === 'dc' && (
                    <div className="flex flex-col items-center gap-4 w-full px-2">
                        <div className="text-center w-full">
                            <h3 className="font-medium text-text-primary mb-1">Bot Configuration</h3>
                            <p className="text-xs text-text-tertiary">Discord requires a dedicated Bot Token to operate.</p>
                        </div>

                        <div className="w-full flex flex-col gap-3">
                            <div className="flex flex-col gap-1">
                                <label className="text-[10px] text-text-tertiary font-mono">Bot Token (Required)</label>
                                <input
                                    type="password"
                                    value={discordBotToken}
                                    onChange={e => setDiscordBotToken(e.target.value)}
                                    placeholder="Enter bot token"
                                    className="w-full bg-layer-divider border border-layer-3 rounded px-3 py-2 text-sm text-text-primary outline-none focus:border-layer-4 transition-colors font-mono"
                                />
                                <a href="https://discord.com/developers/applications" target="_blank" rel="noreferrer" className="text-[10px] text-blue-400 hover:underline">Get your token from Discord Developer Portal</a>
                            </div>

                            <div className="flex flex-col gap-1">
                                <label className="text-[10px] text-text-tertiary font-mono">Guild ID (Optional)</label>
                                <input
                                    type="text"
                                    value={discordGuildId}
                                    onChange={e => setDiscordGuildId(e.target.value)}
                                    placeholder="Optional Server ID"
                                    className="w-full bg-layer-divider border border-layer-3 rounded px-3 py-2 text-sm text-text-primary outline-none focus:border-layer-4 transition-colors font-mono"
                                />
                            </div>
                        </div>

                        {error && <p className="text-red-400 text-xs mt-2">{error}</p>}

                        <button
                            onClick={handleDiscordPhase2}
                            disabled={isLoading || !discordBotToken}
                            className="bg-green-600 hover:bg-green-500 text-white font-medium py-2 px-6 rounded-lg transition-colors disabled:opacity-50 w-full mt-2"
                        >
                            {isLoading ? 'Activating...' : 'Activate Bot'}
                        </button>
                    </div>
                )}

            </div>
        </SharedModalShell>
    );
};
