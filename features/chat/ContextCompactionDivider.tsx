import React from 'react';

/**
 * ContextCompactionDivider — Visual divider rendered inline in the transcript
 * when the context window has been compacted.
 *
 * Production behavior:
 *  - Inserted as a transcript entry with `isCompaction: true` (already in types.ts)
 *  - Displays a gradient horizontal line with "Context Manifold Compacted" label
 *  - If tokenCount is provided, shows "N tokens freed" beneath
 *  - CSS fade-in animation on mount
 *
 * NOTE: This component exists as a STANDALONE reusable version.
 * The actual rendering is ALSO inline in TerminalView.tsx (lines 31-40)
 * where it already checks `t.isCompaction`. This component can be used
 * when a standalone insertion is needed outside the transcript map.
 */
interface ContextCompactionDividerProps {
    /** Number of tokens freed by compaction, if available */
    tokenCount?: number;
    /** Optional timestamp of the compaction event */
    timestamp?: string;
}

export const ContextCompactionDivider: React.FC<ContextCompactionDividerProps> = ({
    tokenCount,
    timestamp,
}) => {
    return (
        <div className="compaction-divider" role="separator" aria-label="Context compaction event">
            <div className="compaction-divider__line" />
            <div className="compaction-divider__content">
                <div className="compaction-divider__label">
                    Context Manifold Compacted
                </div>
                {tokenCount != null && tokenCount > 0 && (
                    <div className="compaction-divider__tokens">
                        {tokenCount.toLocaleString()} tokens freed
                    </div>
                )}
                {timestamp && (
                    <div className="compaction-divider__time">
                        {new Date(timestamp).toLocaleTimeString()}
                    </div>
                )}
            </div>
            <div className="compaction-divider__line" />
        </div>
    );
};

export default ContextCompactionDivider;
