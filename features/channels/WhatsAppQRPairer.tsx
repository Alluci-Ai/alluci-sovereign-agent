import React, { useState, useEffect } from 'react';
import { useStore } from '../../store/useStore';
import { QrCode, RefreshCcw, CheckCircle, WifiOff } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

export const WhatsAppQRPairer: React.FC = () => {
    const { accessToken } = useStore();
    const [state, setState] = useState<'IDLE' | 'QR_PENDING' | 'CONNECTED' | 'DISCONNECTED'>('IDLE');
    const [qrCode, setQrCode] = useState<string | null>(null);
    const [countdown, setCountdown] = useState(30);

    const checkStatus = async () => {
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/channels/whatsapp/status`, {
                headers: { 'Authorization': `Bearer ${accessToken}` },
                credentials: 'include'
            });
            if (res.ok) {
                const data = await res.json();
                setState(data.status); // Expecting IDLE, QR_PENDING, CONNECTED, DISCONNECTED
                if (data.status === 'QR_PENDING' && data.qrCode) {
                    setQrCode(data.qrCode); // Base64 image payload
                    setCountdown(30); // Reset timeout on fresh payload
                }
            }
        } catch (err) {
            console.error('Failed fetching WA status', err);
            setState('DISCONNECTED');
        }
    };

    useEffect(() => {
        if (state === 'QR_PENDING') {
            const timer = setInterval(() => {
                setCountdown(prev => {
                    if (prev <= 1) {
                        checkStatus(); // Force refresh native string natively avoiding stale timeouts
                        return 30;
                    }
                    return prev - 1;
                });
            }, 1000);
            return () => clearInterval(timer);
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [state]);

    const requestPairing = async () => {
        setState('QR_PENDING');
        // Initial manual trigger
        checkStatus();
    };

    return (
        <div className="bg-glass-2 border border-glass-edge rounded-lg p-4 flex flex-col items-center gap-3">
            <div className="w-full flex justify-between items-center mb-2">
                <span className="text-[10px] glass-label text-text-tertiary uppercase flex items-center gap-1">
                    <QrCode size={12} /> WhatsApp Web Authentication
                </span>
                {state === 'QR_PENDING' && <span className="text-[10px] font-mono opacity-80 animate-pulse text-accent">Expires: {countdown}s</span>}
            </div>

            {state === 'IDLE' && (
                <button onClick={requestPairing} className="glass-btn flex items-center gap-2 w-full justify-center">
                    <RefreshCcw size={14} /> Generate Pairing Link
                </button>
            )}

            {state === 'QR_PENDING' && qrCode && (
                <div className="flex flex-col items-center gap-2">
                    <div className="bg-white p-2 rounded-lg relative overflow-hidden">
                        <img src={`data:image/png;base64,${qrCode}`} alt="WhatsApp QR Code" className="w-48 h-48 opacity-90 transition-opacity duration-300" />
                    </div>
                    <span className="text-[9px] opacity-50 font-mono text-center max-w-[200px]">Scan with WhatsApp Business app to securely map OS gateway keys digitally.</span>
                </div>
            )}

            {state === 'CONNECTED' && (
                <div className="flex flex-col items-center gap-2 p-4 text-status-good animate-in fade-in duration-500">
                    <CheckCircle size={32} />
                    <span className="text-xs font-mono tracking-widest">GATEWAY LINKED</span>
                </div>
            )}

            {state === 'DISCONNECTED' && (
                <div className="flex flex-col items-center gap-2 p-4 text-text-tertiary">
                    <WifiOff size={32} className="opacity-50" />
                    <span className="text-xs">Offline</span>
                    <button onClick={requestPairing} className="glass-btn mt-2">Retry</button>
                </div>
            )}
        </div>
    );
};

export default WhatsAppQRPairer;
