import React from 'react';
import { Artifact } from '../../../types';

export interface RendererProps {
  artifact: Artifact;
  pageIndex: number;
  onPageChange: (index: number) => void;
}

export const TextRenderer: React.FC<RendererProps> = ({ artifact }) => {
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        minHeight: '400px',
        padding: '20px',
        background: 'var(--color-bg-tertiary, #181825)',
        color: 'var(--color-text-primary, #cdd6f4)',
        borderRadius: '8px',
        fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        fontSize: '14px',
        lineHeight: '1.6',
        overflowY: 'auto',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word'
      }}
    >
      {artifact.content || 'Empty text artifact.'}
    </div>
  );
};
