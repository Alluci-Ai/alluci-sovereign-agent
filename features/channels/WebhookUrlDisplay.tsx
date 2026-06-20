import React, { useState } from 'react';
import { Link, Copy, Check } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

interface WebhookUrlDisplayProps {
    channelId: string;
    secret: string;
}

export const WebhookUrlDisplay: React.FC<WebhookUrlDisplayProps> = ({ channelId, secret }) => {
    const [copied, setCopied] = useState(false);

    // Construct local or external facing gateway URI map
    const webhookUrl = `${DAEMON_URL}/api/webhook/${channelId}/${secret}`;

    const handleCopy = () => {
        navigator.clipboard.writeText(webhookUrl);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="flex flex-col gap-1">
            <label className="text-[10px] text-text-tertiary font-mono flex items-center gap-1">
                <Link size={10} /> Inbound Webhook Dispatch URI
            </label>
            <div className="flex items-center gap-0 w-full relative">
                <input
                    type="text"
                    readOnly
                    value={webhookUrl}
                    className="glass-input text-[10px] w-full font-mono bg-black/20 text-text-secondary pr-10 border-r-0 rounded-r-none cursor-text select-all"
                />
                <button
                    onClick={handleCopy}
                    className="h-full px-3 py-1 bg-glass-pressed border border-glass-edge border-l-0 rounded-r-lg hover:bg-glass-hover hover:text-accent transition-colors text-text-tertiary flex items-center justify-center flex-shrink-0"
                    title="Copy payload routing URI"
                    style={{ minHeight: '30px' }} // Match glass-input internal pad dimensions 
                >
                    {copied ? <Check size={14} className="text-status-good" /> : <Copy size={14} />}
                </button>
            </div>
        </div>
    );
};

export default WebhookUrlDisplay;
