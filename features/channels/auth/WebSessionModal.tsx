import React, { useState } from 'react';
import { Connection } from '../../../types';
import { SharedModalShell } from './SharedModalShell';
import { activateBridge, saveBridgeCredentials } from '../../../lib/bridgeAuth';
import { useStore } from '../../../store/useStore';
import { DAEMON_URL } from '../../../usePolytopeAPI';

export const WebSessionModal: React.FC<{
    connection: Connection;
    onComplete: (session: string, img: string) => void;
    onCancel: () => void;
}> = ({ connection, onComplete, onCancel }) => {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const bridgeId = connection.id;
    const accessToken = useStore(state => state.accessToken);

    // WebChat specifics
    const [targetUrl, setTargetUrl] = useState("https://");
    const [sessionName, setSessionName] = useState("");
    const [isLaunched, setIsLaunched] = useState(false);

    const handleLaunch = async () => {
        if (!targetUrl.startsWith('http')) {
            setError("Must be a valid URL starting with http:// or https://");
            return;
        }
        setIsLoading(true);
        setError(null);
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/channels/webchat/launch`, {
                method: 'POST',
                headers: { 
                    'Authorization': `Bearer ${accessToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ url: targetUrl }),
                credentials: 'include'
            });
            if (!res.ok) throw new Error(await res.text());
            setIsLaunched(true);
        } catch (e: any) {
            setError(e.message || "Failed to launch browser instance");
        } finally {
            setIsLoading(false);
        }
    };

    const handleCapture = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const token = localStorage.getItem('alluci_daemon_token');
            // Call real backend capture endpoint
            // No more playwright_mock_!
            const res = await fetch(`${DAEMON_URL}/api/channels/webchat/session/active/capture`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ 
                    target_url: targetUrl,
                    session_name: sessionName || 'Default Session'
                })
            });

            if (!res.ok) throw new Error(await res.text());
            const creds = await res.json();

            const saved = await saveBridgeCredentials(bridgeId, creds, accessToken || "");
            if (!saved) throw new Error("Failed to secure browser session tokens");

            const activated = await activateBridge(bridgeId, accessToken || "");
            if (!activated?.connected) throw new Error(`Bridge activation failed.`);

            onComplete(JSON.stringify(creds), "");
        } catch (e: any) {
            setError(e.message || "Capture Failed");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <SharedModalShell connection={connection} onCancel={onCancel}>
            <div className="flex flex-col gap-4 text-white p-4 items-center w-full">
                <p className="text-text-secondary text-sm text-center mb-2">
                    Universal <strong>WebChat</strong> Session Capture. The agent will launch a browser for you to log in, and then securely capture the session state to the isolated vault.
                </p>

                <div className="w-full max-w-[280px] flex flex-col gap-3">
                    <div className="flex flex-col gap-1">
                        <label className="text-[10px] text-text-tertiary font-mono">Target Chat URL</label>
                        <input
                            type="text"
                            value={targetUrl}
                            onChange={e => setTargetUrl(e.target.value)}
                            disabled={isLaunched}
                            placeholder="https://client.example.com"
                            className="w-full bg-layer-divider border border-layer-3 rounded px-3 py-2 text-sm text-text-primary outline-none disabled:opacity-50 font-mono"
                        />
                    </div>

                    <div className="flex flex-col gap-1">
                        <label className="text-[10px] text-text-tertiary font-mono">Session Label (Optional)</label>
                        <input
                            type="text"
                            value={sessionName}
                            onChange={e => setSessionName(e.target.value)}
                            disabled={isLaunched}
                            placeholder="e.g. Work Portal"
                            className="w-full bg-layer-divider border border-layer-3 rounded px-3 py-2 text-sm text-text-primary outline-none disabled:opacity-50"
                        />
                    </div>

                    {!isLaunched ? (
                        <button
                            onClick={handleLaunch}
                            disabled={isLoading}
                            className="bg-blue-600/80 hover:bg-blue-500 text-white font-medium py-2 px-6 rounded-lg transition-colors disabled:opacity-50 w-full mt-2"
                        >
                            {isLoading ? 'Launching Chrome...' : 'Launch Login Browser'}
                        </button>
                    ) : (
                        <div className="flex flex-col rounded border border-green-500/30 overflow-hidden mt-2">
                            <div className="bg-green-500/10 p-3 text-center">
                                <div className="animate-pulse bg-green-500 w-2 h-2 rounded-full inline-block mr-2"></div>
                                <span className="text-xs text-green-400">Browser Active</span>
                            </div>
                            <div className="p-3 bg-layer-2 text-center text-xs text-text-secondary">
                                Please complete the login process in the newly opened browser window.
                                <br /><br />
                                Once you see the chat interface, click below.
                            </div>
                            <button
                                onClick={handleCapture}
                                disabled={isLoading}
                                className="bg-green-600 hover:bg-green-500 text-white font-medium py-3 rounded-none transition-colors disabled:opacity-50 w-full"
                            >
                                {isLoading ? 'Securing Session Data...' : 'Done — Capture Session'}
                            </button>
                        </div>
                    )}
                </div>

                {error && <p className="text-red-400 text-xs text-center">{error}</p>}
            </div>
        </SharedModalShell>
    );
};
