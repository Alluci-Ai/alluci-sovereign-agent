import React, { useState, useCallback } from 'react';
import { Copy, Check } from 'lucide-react';

interface CopyMessageButtonProps {
    text: string;
}

/**
 * CopyMessageButton — Hoverable icon to copy message text to the clipboard.
 * Shown via group-hover CSS. Provides brief "Copied!" feedback state.
 */
export const CopyMessageButton: React.FC<CopyMessageButtonProps> = ({ text }) => {
    const [copied, setCopied] = useState(false);

    const handleCopy = useCallback(async () => {
        try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy text: ', err);
        }
    }, [text]);

    return (
        <button
            onClick={handleCopy}
            className="absolute -top-3 -right-3 opacity-0 group-hover:opacity-100 transition-opacity bg-glass-1 backdrop-blur-md border border-glass-edge rounded-full px-2 py-1.5 shadow-md z-10 hover:bg-glass-hover text-[10px] glass-label text-text-primary flex items-center gap-1"
            title="Copy to Clipboard"
            aria-label="Copy message"
        >
            {copied ? (
                <>
                    <Check size={12} className="text-status-good" />
                    <span>Copied!</span>
                </>
            ) : (
                <Copy size={12} />
            )}
        </button>
    );
};

export default CopyMessageButton;
