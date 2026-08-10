import React from 'react';
import { Artifact } from '../../../types';

export interface RendererProps {
  artifact: Artifact;
  pageIndex: number;
  onPageChange: (index: number) => void;
}

export const PresentationRenderer: React.FC<RendererProps> = ({ artifact, pageIndex, onPageChange }) => {
  const pages = artifact.pages || [];
  const currentPage = pages[pageIndex];

  if (!currentPage && !artifact.content) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: 'var(--color-text-secondary, #94a3b8)' }}>
        No presentation slides available.
      </div>
    );
  }

  const slideHtml = currentPage?.html || artifact.content || '';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100%', gap: '12px' }}>
      <div
        style={{
          flex: 1,
          width: '100%',
          minHeight: '400px',
          background: '#ffffff',
          borderRadius: '8px',
          overflow: 'hidden',
          boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        <iframe
          srcDoc={slideHtml}
          title={currentPage?.title || `Slide ${pageIndex + 1}`}
          sandbox="allow-scripts"
          style={{ width: '100%', height: '100%', border: 'none' }}
        />
      </div>

      {pages.length > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', padding: '8px 0' }}>
          <button
            disabled={pageIndex === 0}
            onClick={() => onPageChange(Math.max(0, pageIndex - 1))}
            style={{
              padding: '6px 16px',
              borderRadius: '6px',
              border: 'none',
              background: 'rgba(255,255,255,0.1)',
              color: '#fff',
              cursor: pageIndex === 0 ? 'not-allowed' : 'pointer',
              opacity: pageIndex === 0 ? 0.5 : 1
            }}
          >
            Previous Slide
          </button>
          <span style={{ display: 'flex', alignItems: 'center', fontSize: '13px', color: '#94a3b8' }}>
            {pageIndex + 1} of {pages.length}
          </span>
          <button
            disabled={pageIndex === pages.length - 1}
            onClick={() => onPageChange(Math.min(pages.length - 1, pageIndex + 1))}
            style={{
              padding: '6px 16px',
              borderRadius: '6px',
              border: 'none',
              background: 'rgba(255,255,255,0.1)',
              color: '#fff',
              cursor: pageIndex === pages.length - 1 ? 'not-allowed' : 'pointer',
              opacity: pageIndex === pages.length - 1 ? 0.5 : 1
            }}
          >
            Next Slide
          </button>
        </div>
      )}
    </div>
  );
};
