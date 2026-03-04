import React, { useEffect, useState } from 'react';
import { Apple } from 'lucide-react';

export const IMessagePlatformGuard: React.FC = () => {
    const [isMac, setIsMac] = useState(true); // Default to assuming mapped locally

    useEffect(() => {
        // Native detection of window navigator
        const platform = window.navigator?.platform || '';
        if (!platform.toLowerCase().includes('mac')) {
            setIsMac(false);
        }
    }, []);

    if (isMac) return null;

    return (
        <div className="absolute top-2 right-2 bg-glass-1 border border-status-error/40 text-status-error text-[9px] px-2 py-1 rounded shadow-sm backdrop-blur-md flex items-center gap-1 font-mono tracking-widest uppercase animate-in zoom-in-95 pointer-events-none">
            <Apple size={10} />
            macOS Required
        </div>
    );
};

export default IMessagePlatformGuard;
