import React from 'react';

export interface SourceAttributionProps {
    modelName?: string;
    tokenCount?: number;
}

/**
 * SourceAttribution — displays truncated metadata below an AI message 
 * showing the inference model used and the token cost.
 */
export const SourceAttribution: React.FC<SourceAttributionProps> = ({ modelName, tokenCount }) => {
    if (!modelName && !tokenCount) return null;

    return (
        <div className="mt-2 text-[10px] glass-label text-text-tertiary flex items-center gap-2 px-1">
            {modelName && (
                <span>via {modelName}</span>
            )}
            {modelName && tokenCount && (
                <span className="opacity-50">•</span>
            )}
            {tokenCount != null && (
                <span>{tokenCount.toLocaleString()} tokens</span>
            )}
        </div>
    );
};

export default SourceAttribution;
