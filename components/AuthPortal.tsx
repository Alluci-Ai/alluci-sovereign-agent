
import React, { useState } from 'react';
import { Connection } from '../types';
import { VerusIdLogin } from '../features/bridges/VerusIdLogin';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

export const AuthPortal: React.FC<{
    connection: Connection;
    onComplete: (session: string, img: string) => void;
    onCancel: () => void;
}> = ({ connection, onComplete, onCancel }) => {
    const [isLoading, setIsLoading] = useState(false);
    const [isVerifying, setIsVerifying] = useState(false);

    const isVerus = connection.id === 'verus';

    const handleAuth = () => {
        if (isVerus) return; // Managed by QR flow
        setIsLoading(true);
        setTimeout(() => {
            setIsLoading(false);
            setIsVerifying(true);
            setTimeout(() => {
                onComplete(`active_${connection.id.toLowerCase()}_session`, `https://api.dicebear.com/7.x/identicon/svg?seed=${connection.id}`);
            }, 1500);
        }, 1200);
    };

    return (
        <div className="fixed inset-0 z-[250] flex items-center justify-center bg-black/80 backdrop-blur-xl p-4">
            <div className="w-full max-w-sm flex flex-col items-center">
                <div className="h-1.5 w-full flex absolute top-0 left-0"><div className="h-full bg-sovereign flex-1" /><div className="h-full bg-agent flex-1" /><div className="h-full bg-tension flex-1" /><div className="h-full bg-flux flex-1" /></div>
                <div className="flex justify-between items-center border-b border-sovereign pb-6 mb-8 mt-2">
                    <div className="flex flex-col">
                        <span className="glass-label text-[12px] md:text-[14px] tracking-[0.4em]">{isVerus ? 'VERUSID_SOVEREIGN_LINK' : 'SECURE_HANDSHAKE'}</span>
                        <span className="text-[8px] font-mono opacity-40 uppercase">{connection.name} Manifold</span>
                    </div>
                    <button onClick={onCancel} className="text-secondary hover:text-black transition-colors px-2 py-1">✕</button>
                </div>

                <div className="flex flex-col gap-6 w-full">
                    {isVerus ? (
                        <VerusIdLogin
                            onComplete={(identity) => onComplete(`verus_${identity}`, `https://api.dicebear.com/7.x/identicon/svg?seed=${identity}`)}
                            onCancel={onCancel}
                        />
                    ) : (
                        <>
                            {!isVerifying ? (
                                <>
                                    <div className="text-center mb-4">
                                        <div className="w-16 h-16  rounded-full flex items-center justify-center mx-auto mb-4 border border-zinc/10">
                                            <span className="text-2xl font-bold">{connection.name.slice(0, 1)}</span>
                                        </div>
                                        <h3 className="text-[12px] font-sans font-bold">Initiate {connection.name} Bridge</h3>
                                        <p className="text-[10px] opacity-60 max-w-[280px] mx-auto mt-2 leading-relaxed">
                                            Connecting via <span className="text-agent font-bold">{connection.authType}</span> protocol.
                                            Enforced isolation and end-to-end encryption.
                                        </p>
                                    </div>
                                    <button disabled={isLoading} onClick={handleAuth} className={`w-full p-4 glass-label text-[10px] flex items-center justify-center gap-3 transition-all ${isLoading ? 'bg-zinc text-white animate-pulse' : 'bg-sovereign text-white hover:bg-agent'}`}>
                                        {isLoading ? '[ NEGOTIATING... ]' : '[ AUTHORIZE_ONE_TOUCH ]'}
                                    </button>
                                </>
                            ) : (
                                <div className="flex flex-col items-center gap-6 py-4">
                                    <div className="relative">
                                        <div className="w-20 h-20 rounded-full border-4 border-agent animate-ping absolute opacity-20" />
                                        <div className="w-20 h-20 rounded-full border-2 border-agent flex items-center justify-center">
                                            <svg className="w-10 h-10 text-agent animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4" />
                                            </svg>
                                        </div>
                                    </div>
                                    <div className="text-[10px] font-mono text-center tracking-widest text-agent uppercase animate-pulse">Verification_In_Progress</div>
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};
