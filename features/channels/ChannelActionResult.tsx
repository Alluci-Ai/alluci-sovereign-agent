import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Activity } from 'lucide-react';

interface ChannelActionResultProps {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    result: any;
    onDismiss: () => void;
}

export const ChannelActionResult: React.FC<ChannelActionResultProps> = ({ result, onDismiss }) => {
    const [expanded, setExpanded] = useState(false);

    if (!result) return null;

    return (
        <div className="mt-2 text-xs font-mono border border-glass-edge bg-black/40 rounded-md overflow-hidden relative break-words z-20">
            <div
                className={`p-2 flex items-center justify-between cursor-pointer hover:bg-white/5 transition-colors border-l-2 ${result.status === 'ok' ? 'border-status-good' : 'border-status-error'}`}
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-center gap-2">
                    {expanded ? <ChevronDown size={14} className="text-text-tertiary" /> : <ChevronRight size={14} className="text-text-tertiary" />}
                    <Activity size={12} className={result.status === 'ok' ? "text-status-good" : "text-status-error"} />
                    <span className="text-text-secondary truncate max-w-[150px]">
                        {result.status === 'ok' ? 'Action Completed' : 'Action Failed'}
                    </span>
                </div>

                <button
                    onClick={(e) => { e.stopPropagation(); onDismiss(); }}
                    className="text-[9px] glass-label opacity-50 hover:opacity-100 hover:text-status-error transition-all"
                >
                    DISMISS
                </button>
            </div>

            {expanded && (
                <div className="p-2 border-t border-glass-edge bg-glass-1">
                    <pre className="text-[10px] text-text-tertiary opacity-80 whitespace-pre-wrap">
                        {typeof result === 'string' ? result : JSON.stringify(result, null, 2)}
                    </pre>
                </div>
            )}
        </div>
    );
};

export default ChannelActionResult;
