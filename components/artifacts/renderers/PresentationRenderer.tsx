import React, { useMemo } from 'react';
import { Artifact } from '../../../types';
import { TextRenderer } from './TextRenderer';

export interface RendererProps {
  artifact: Artifact;
  pageIndex: number;
  onPageChange: (index: number) => void;
}

export const PresentationRenderer: React.FC<RendererProps> = ({ artifact, pageIndex, onPageChange }) => {
  const pages = artifact.pages || [];

  // Parse slides from content if pages array is empty
  const parsedSlides = useMemo(() => {
    if (pages.length > 0) return pages.map(p => ({ title: p.title, html: p.html, content: p.html }));

    const rawContent = artifact.content || '';
    if (!rawContent) return [];

    // Split content by '---' slide separators or '## Slide' headers
    let slideBlocks = rawContent.split(/\n(?=---|## Slide)/g).map(s => s.replace(/^---/g, '').trim()).filter(Boolean);
    if (slideBlocks.length <= 1) {
      slideBlocks = rawContent.split(/\n\n(?=## )/g).map(s => s.trim()).filter(Boolean);
    }

    return slideBlocks.map((block, idx) => {
      const firstLine = block.split('\n')[0].replace(/^#+\s*/, '').trim();
      return {
        title: firstLine || `Slide ${idx + 1}`,
        html: '',
        content: block
      };
    });
  }, [pages, artifact.content]);

  const slideCount = Math.max(parsedSlides.length, 1);
  const currentSlide = parsedSlides[pageIndex] || parsedSlides[0];

  if (!currentSlide && !artifact.content) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        No presentation slides available.
      </div>
    );
  }

  const isHtml = currentSlide?.html && currentSlide.html.trim().startsWith('<');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100%', gap: '12px' }}>
      <div
        style={{
          flex: 1,
          width: '100%',
          minHeight: '380px',
          background: 'var(--bg-elevated)',
          border: '1px solid var(--glass-edge)',
          borderRadius: '12px',
          overflow: 'auto',
          boxShadow: '0 4px 20px rgba(0,0,0,0.3)',
          display: 'flex',
          flexDirection: 'column',
          padding: '24px'
        }}
      >
        {isHtml ? (
          <iframe
            srcDoc={currentSlide.html}
            title={currentSlide.title || `Slide ${pageIndex + 1}`}
            sandbox="allow-scripts"
            style={{ width: '100%', height: '100%', border: 'none' }}
          />
        ) : (
          <TextRenderer
            artifact={{
              ...artifact,
              content: currentSlide?.content || artifact.content
            }}
            pageIndex={0}
            onPageChange={() => {}}
          />
        )}
      </div>

      {slideCount > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '12px', padding: '6px 0' }}>
          <button
            disabled={pageIndex === 0}
            onClick={() => onPageChange(Math.max(0, pageIndex - 1))}
            style={{
              padding: '6px 14px',
              borderRadius: '6px',
              border: '1px solid var(--glass-edge)',
              background: 'var(--fill-tertiary)',
              color: 'var(--text-primary)',
              cursor: pageIndex === 0 ? 'not-allowed' : 'pointer',
              opacity: pageIndex === 0 ? 0.4 : 1,
              fontSize: '12px',
              fontWeight: 600
            }}
          >
            ← Previous Slide
          </button>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: 600 }}>
            Slide {pageIndex + 1} of {slideCount}
          </span>
          <button
            disabled={pageIndex === slideCount - 1}
            onClick={() => onPageChange(Math.min(slideCount - 1, pageIndex + 1))}
            style={{
              padding: '6px 14px',
              borderRadius: '6px',
              border: '1px solid var(--glass-edge)',
              background: 'var(--fill-tertiary)',
              color: 'var(--text-primary)',
              cursor: pageIndex === slideCount - 1 ? 'not-allowed' : 'pointer',
              opacity: pageIndex === slideCount - 1 ? 0.4 : 1,
              fontSize: '12px',
              fontWeight: 600
            }}
          >
            Next Slide →
          </button>
        </div>
      )}
    </div>
  );
};
