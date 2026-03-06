import React from 'react';
import { Connection } from '../../../types';

interface SharedModalShellProps {
    connection: Connection;
    title?: string;
    onCancel: () => void;
    children: React.ReactNode;
}

export const SharedModalShell: React.FC<SharedModalShellProps> = ({ connection, title, onCancel, children }) => {
    return (
        <div className="fixed inset-0 z-[250] flex items-center justify-center bg-black/80 backdrop-blur-xl p-4">
            <div className="w-full max-w-sm flex flex-col items-center">
                <div className="h-1.5 w-full flex absolute top-0 left-0">
                    <div className="h-full bg-sovereign flex-1" />
                    <div className="h-full bg-agent flex-1" />
                    <div className="h-full bg-tension flex-1" />
                    <div className="h-full bg-flux flex-1" />
                </div>
                <div className="flex justify-between items-center border-b border-sovereign pb-6 mb-8 mt-2 w-full">
                    <div className="flex flex-col text-left">
                        <span className="glass-label text-[12px] md:text-[14px] tracking-[0.4em]">
                            {title || 'SECURE_HANDSHAKE'}
                        </span>
                        <span className="text-[8px] font-mono opacity-40 uppercase">{connection.name} Manifold</span>
                    </div>
                    <button onClick={onCancel} className="text-secondary hover:text-black transition-colors px-2 py-1">✕</button>
                </div>
                <div className="flex flex-col gap-6 w-full">
                    {children}
                </div>
            </div>
        </div>
    );
};
