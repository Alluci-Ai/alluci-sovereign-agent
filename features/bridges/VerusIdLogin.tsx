
import React, { useState, useEffect } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { Shield, Smartphone, ExternalLink, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

interface VerusIdLoginProps {
    onComplete: (identity: string) => void;
    onCancel: () => void;
}

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://127.0.0.1:8000';

export const VerusIdLogin: React.FC<VerusIdLoginProps> = ({ onComplete, onCancel }) => {
    const [loginData, setLoginData] = useState<any>(null);
    const [status, setStatus] = useState<'idle' | 'loading' | 'pending' | 'verifying' | 'success' | 'error'>('idle');
    const [error, setError] = useState<string | null>(null);

    const fetchLoginRequest = async () => {
        setStatus('loading');
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/auth/verusid/login-request`);
            if (!res.ok) throw new Error("Failed to fetch login request");

            const data = await res.json();
            setLoginData(data);
            setStatus('pending');
        } catch (err: any) {
            setError(err.message);
            setStatus('error');
        }
    };

    useEffect(() => {
        fetchLoginRequest();
    }, []);

    // Real polling for status
    useEffect(() => {
        if (status !== 'pending' || !loginData) return;

        // The challenge_id is returned at the top level of the response
        const challengeId = loginData.challenge_id;
        if (!challengeId) return;

        const interval = setInterval(async () => {
            try {
                const res = await fetch(`${DAEMON_URL}/api/v1/auth/verusid/status/${challengeId}`);
                if (!res.ok) return;

                const data = await res.json();
                if (data.status === 'SUCCESS') {
                    setStatus('success');
                    clearInterval(interval);

                    // Store access token
                    if (data.access_token) {
                        localStorage.setItem('alluci_access_token', data.access_token);
                    }

                    // Delay calling onComplete to show success state
                    setTimeout(() => {
                        onComplete(data.identity);
                    }, 1500);
                }
            } catch (err) {
                console.error("Status polling failed:", err);
            }
        }, 3000);

        return () => clearInterval(interval);
    }, [status, loginData, onComplete]);

    const handleDeeplink = () => {
        if (loginData?.deeplink) {
            window.location.href = loginData.deeplink;
        }
    };

    return (
        <div className="verus-login-container">
            <div className="verus-login-glass">
                {/* Specular highlights */}
                <div className="glass-glint-1" />
                <div className="glass-glint-2" />

                <div className="glass-header">
                    <div className="flex items-center gap-3">
                        <div className="verus-logo-glow">
                            <Shield className="text-white w-5 h-5" />
                        </div>
                        <div>
                            <h2 className="text-sm font-bold tracking-widest uppercase">VerusID Login</h2>
                            <p className="text-[10px] opacity-40 font-mono italic">SSID Challenge-Response</p>
                        </div>
                    </div>
                    <button onClick={onCancel} className="close-btn">✕</button>
                </div>

                <div className="glass-content">
                    {status === 'loading' && (
                        <div className="flex flex-col items-center justify-center h-64 gap-4">
                            <Loader2 className="w-8 h-8 animate-spin text-accent" />
                            <span className="glass-label text-[10px] animate-pulse">[ NEGOTIATING_VDXF_PRIMES ]</span>
                        </div>
                    )}

                    {status === 'error' && (
                        <div className="flex flex-col items-center justify-center min-h-[256px] gap-4 text-center px-4">
                            <AlertCircle className="w-10 h-10 text-red-500 opacity-80" />
                            <div className="space-y-2">
                                <p className="text-[11px] text-red-400 font-bold uppercase tracking-wider">Configuration Error</p>
                                <p className="text-[10px] text-white/60 leading-relaxed font-mono">
                                    {error?.includes("CONFIGURATION_ERROR")
                                        ? "Private Key (WIF) is missing from .env. Please configure your VerusID authority to enable SSID login."
                                        : error}
                                </p>
                            </div>
                            <button onClick={fetchLoginRequest} className="glass-btn text-[10px] mt-4 py-2 px-6">Retry Connection</button>
                        </div>
                    )}

                    {status === 'pending' && loginData && (
                        <div className="flex flex-col items-center gap-6 animate-in fade-in duration-700">
                            <div className="qr-frame">
                                <QRCodeSVG
                                    value={JSON.stringify(loginData.request)}
                                    size={180}
                                    level="L"
                                    includeMargin={false}
                                    className="qr-canvas"
                                />
                                <div className="qr-corners" />
                            </div>

                            <div className="text-center space-y-2">
                                <h3 className="text-[11px] font-bold text-white/80">Scan with Verus Mobile</h3>
                                <p className="text-[10px] opacity-50 px-6 leading-relaxed">
                                    Authenticate as <span className="text-accent">{loginData.request?.signing_id || "Sovereign Agent"}</span> using your decentralized identity.
                                </p>
                            </div>

                            <button
                                onClick={handleDeeplink}
                                className="deeplink-btn"
                            >
                                <Smartphone className="w-4 h-4" />
                                <span>Open in Verus Mobile</span>
                                <ExternalLink className="w-3 h-3 opacity-50" />
                            </button>

                            <div className="sync-status">
                                <span className="dot animate-ping" />
                                <span className="text-[9px] font-mono tracking-tighter opacity-40 uppercase">Awaiting Signature Verification</span>
                            </div>
                        </div>
                    )}

                    {status === 'success' && (
                        <div className="flex flex-col items-center justify-center h-64 gap-4 animate-in zoom-in duration-500">
                            <CheckCircle2 className="w-12 h-12 text-accent" />
                            <div className="text-center">
                                <h3 className="text-sm font-bold">Authenticated</h3>
                                <p className="text-[10px] opacity-60">Identity Linked Successfully</p>
                            </div>
                        </div>
                    )}
                </div>

                <div className="glass-footer">
                    <div className="security-tag">
                        <Shield className="w-3 h-3" />
                        <span>Quantum-Resistant Identity</span>
                    </div>
                </div>
            </div>

            <style>{`
                .verus-login-container {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    width: 100%;
                }
                .verus-login-glass {
                    position: relative;
                    width: 100%;
                    max-width: 320px;
                    background: rgba(255, 255, 255, 0.03);
                    backdrop-filter: blur(24px) saturate(180%);
                    -webkit-backdrop-filter: blur(24px) saturate(180%);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 28px;
                    overflow: hidden;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                }
                .glass-glint-1 {
                    position: absolute;
                    top: -10%;
                    left: -10%;
                    width: 40%;
                    height: 40%;
                    background: radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 70%);
                    pointer-events: none;
                }
                .glass-header {
                    padding: 20px;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .verus-logo-glow {
                    width: 32px;
                    height: 32px;
                    background: linear-gradient(135deg, #3100D1 0%, #0077FF 100%);
                    border-radius: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 0 15px rgba(0, 119, 255, 0.3);
                }
                .close-btn {
                    width: 28px;
                    height: 28px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: rgba(255, 255, 255, 0.3);
                    transition: all 0.2s;
                }
                .close-btn:hover {
                    background: rgba(255, 255, 255, 0.05);
                    color: white;
                }
                .glass-content {
                    padding: 24px;
                }
                .qr-frame {
                    position: relative;
                    padding: 12px;
                    background: white;
                    border-radius: 20px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                }
                .qr-canvas {
                    border-radius: 8px;
                }
                .deeplink-btn {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    width: 100%;
                    padding: 14px;
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 16px;
                    font-size: 11px;
                    font-weight: 500;
                    color: white;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                }
                .deeplink-btn:hover {
                    background: rgba(255, 255, 255, 0.08);
                    transform: translateY(-1px);
                    border-color: rgba(255, 255, 255, 0.15);
                }
                .deeplink-btn:active {
                    transform: scale(0.98);
                }
                .sync-status {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding-top: 10px;
                }
                .dot {
                    width: 6px;
                    height: 6px;
                    background: #0077FF;
                    border-radius: 50%;
                }
                .glass-footer {
                    padding: 16px 20px;
                    background: rgba(0, 0, 0, 0.1);
                    display: flex;
                    justify-content: center;
                }
                .security-tag {
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    font-size: 8px;
                    font-family: var(--font-mono);
                    text-transform: uppercase;
                    letter-spacing: 0.1em;
                    color: rgba(255, 255, 255, 0.3);
                }
            `}</style>
        </div>
    );
};
