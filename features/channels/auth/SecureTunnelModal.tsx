import React, { useState } from 'react';
import { Connection } from '../../../types';
import { SharedModalShell } from './SharedModalShell';
import { activateBridge, saveBridgeCredentials } from '../../../lib/bridgeAuth';
import { useStore } from '../../../store/useStore';
import { DAEMON_URL } from '../../../usePolytopeAPI';

export const SecureTunnelModal: React.FC<{
    connection: Connection;
    onComplete: (session: string, img: string) => void;
    onCancel: () => void;
}> = ({ connection, onComplete, onCancel }) => {
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const bridgeId = connection.id;
    const storeToken = useStore(state => state.accessToken);
    const accessToken = storeToken || localStorage.getItem('alluci_access_token') || "";

    // iWatch
    const [pairingCode, setPairingCode] = useState("");
    const [deviceId, setDeviceId] = useState<string | null>(null);

    React.useEffect(() => {
        if (bridgeId === 'iwatch') {
            fetch(`${DAEMON_URL}/api/v1/channels/iwatch/pairing-qr`, {
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            })
            .then(res => res.json())
            .then(data => setDeviceId(data.device_id))
            .catch(console.error);
        }
    }, [bridgeId, accessToken]);

    // iPhone
    const [discoveryMode, setDiscoveryMode] = useState<'MDNS' | 'MANUAL'>('MDNS');
    const [iphoneIp, setIphoneIp] = useState("");

    // iMessage permissions (mock state)
    const [hasCheckedPerms, setHasCheckedPerms] = useState(false);

    const handleImessageCheck = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/channels/imessage/permission`, {
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            });
            const data = await res.json();
            if (data.granted) {
                setHasCheckedPerms(true);
            } else {
                setError(data.error || "Permission denied.");
            }
        } catch (e) {
            setError("Failed to verify macOS permissions.");
        } finally {
            setIsLoading(false);
        }
    };

    const handleSubmit = async () => {
        setIsLoading(true);
        setError(null);
        try {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            let creds: Record<string, any> = {};

            if (bridgeId === 'imessage') {
                if (!hasCheckedPerms) throw new Error("Please verify system permissions first.");
                creds = { permissions_verified: true };
            } else if (bridgeId === 'iwatch') {
                if (!pairingCode) throw new Error("Watch pairing code required.");
                if (!deviceId) throw new Error("Pairing session not initialized. Please try again.");
                
                // Native POST for iWatch pairing
                const res = await fetch(`${DAEMON_URL}/api/v1/channels/iwatch/pair`, {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
                    body: JSON.stringify({ code: pairingCode, device_id: deviceId }),
                    credentials: 'include'
                });
                const data = await res.json();
                if (data.status !== "SUCCESS") throw new Error(data.error || "Pairing failed.");
                
                onComplete(JSON.stringify({ paired: true, deviceId }), "");
                return; // Early return since iWatch doesn't use standard generic save/activate below
            } else if (bridgeId === 'iphone') {
                if (discoveryMode === 'MANUAL' && !iphoneIp) throw new Error("IP Address required.");
                creds = { discovery: discoveryMode, ip: iphoneIp };
            }

            const saved = await saveBridgeCredentials(bridgeId, creds, accessToken || "");
            if (!saved) throw new Error("Failed to save tunnel configuration");

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
            <div className="flex flex-col gap-4 text-white p-4 items-center w-full">
                <p className="text-text-secondary text-sm text-center mb-2">
                    Establish a local Secure Tunnel for <strong>{connection.name}</strong>.
                </p>

                {bridgeId === 'imessage' && (
                    <div className="w-full max-w-[280px] flex flex-col gap-3">
                        <div className="bg-layer-2 p-3 rounded border border-layer-3 text-sm flex flex-col gap-2">
                            <p className="text-text-primary mb-1">macOS Permissions Required:</p>
                            <ul className="text-xs text-text-tertiary list-disc pl-4 flex flex-col gap-1">
                                <li><strong>Full Disk Access</strong> (to read chat.db)</li>
                                <li><strong>Automation</strong> (for AppleScript sends)</li>
                                <li><strong>Contacts</strong> (to resolve names)</li>
                            </ul>
                        </div>

                        {!hasCheckedPerms ? (
                            <button
                                onClick={handleImessageCheck}
                                disabled={isLoading}
                                className="bg-layer-3 hover:bg-layer-4 text-white text-xs py-2 px-4 rounded transition-colors w-full"
                            >
                                {isLoading ? 'Scanning Permissions...' : 'Check System Permissions'}
                            </button>
                        ) : (
                            <div className="text-green-400 text-xs text-center p-2 bg-green-400/10 rounded">
                                ✅ Permissions Verified
                            </div>
                        )}
                    </div>
                )}

                {bridgeId === 'iwatch' && (
                    <div className="w-full max-w-[280px] flex flex-col gap-1">
                        <label className="text-[10px] text-text-tertiary font-mono">6-Digit Pairing Code</label>
                        <input
                            type="text"
                            value={pairingCode}
                            onChange={e => setPairingCode(e.target.value)}
                            placeholder="123456"
                            className="w-full bg-layer-divider border border-layer-3 rounded px-3 py-2 text-sm text-text-primary outline-none focus:border-layer-4 transition-colors font-mono tracking-widest text-center"
                        />
                        <p className="text-[10px] text-text-tertiary mt-1 text-center">Enter the code displayed on your Apple Watch.</p>
                    </div>
                )}

                {bridgeId === 'iphone' && (
                    <div className="w-full max-w-[280px] flex flex-col gap-3">
                        <div className="flex bg-layer-2 rounded p-1 mb-2">
                            <button
                                onClick={() => setDiscoveryMode('MDNS')}
                                className={`flex-1 text-xs py-1 rounded transition-colors ${discoveryMode === 'MDNS' ? 'bg-layer-divider text-white' : 'text-text-tertiary hover:text-text-secondary'}`}
                            >Auto (mDNS)</button>
                            <button
                                onClick={() => setDiscoveryMode('MANUAL')}
                                className={`flex-1 text-xs py-1 rounded transition-colors ${discoveryMode === 'MANUAL' ? 'bg-layer-divider text-white' : 'text-text-tertiary hover:text-text-secondary'}`}
                            >Manual IP</button>
                        </div>

                        {discoveryMode === 'MDNS' ? (
                            <div className="bg-layer-2 p-3 rounded text-center">
                                <span className="text-xs text-text-secondary">Agent will automatically discover your iPhone on the local network via zeroconf.</span>
                            </div>
                        ) : (
                            <div className="flex flex-col gap-1">
                                <label className="text-[10px] text-text-tertiary font-mono">Local IP Address</label>
                                <input
                                    type="text"
                                    value={iphoneIp}
                                    onChange={e => setIphoneIp(e.target.value)}
                                    placeholder="192.168.1.100"
                                    className="w-full bg-layer-divider border border-layer-3 rounded px-3 py-2 text-sm text-text-primary outline-none focus:border-layer-4 transition-colors font-mono"
                                />
                            </div>
                        )}
                    </div>
                )}

                {error && <p className="text-red-400 text-xs text-center">{error}</p>}

                <button
                    onClick={handleSubmit}
                    disabled={isLoading || (bridgeId === 'imessage' && !hasCheckedPerms)}
                    className="bg-purple-600/80 hover:bg-purple-600 text-white font-medium py-2 px-6 rounded-lg transition-colors disabled:opacity-50 w-full max-w-[280px] mt-2"
                >
                    {isLoading ? 'Connecting...' : 'Establish Secure Tunnel'}
                </button>
            </div>
        </SharedModalShell>
    );
};
