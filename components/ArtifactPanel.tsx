import React, { useEffect, useMemo, useState } from 'react';
import { X, ZoomIn, ZoomOut, Download, Maximize2, Minimize2, ChevronLeft, ChevronRight } from 'lucide-react';
import { Artifact } from '../types';
import { RendererRegistry } from '../features/artifacts/RendererRegistry';
import { artifactEvents } from '../lib/artifactEvents';

interface Props {
  artifact: Artifact | null;
  onClose: () => void;
  onVersionSelect?: (version: number) => void;
}

export const ArtifactPanel: React.FC<Props> = ({ artifact, onClose }) => {
  const [pageIndex, setPageIndex] = useState(0);
  const [zoom, setZoom] = useState(100);
  const [fullscreen, setFullscreen] = useState(false);

  useEffect(() => {
    setPageIndex(0);
    setZoom(100);
    if (artifact) {
      artifactEvents.emit({ type: 'artifact.open', artifactId: artifact.id, source: 'user' });
    }
  }, [artifact]);

  const pages = artifact?.pages ?? [];
  const pageCount = Math.max(pages.length, 1);

  const handleDownload = () => {
    if (!artifact) return;
    const content = artifact.content ?? pages[pageIndex]?.html ?? '';
    const ext =
      artifact.kind === 'code' ? '.txt' :
      artifact.kind === 'html' || artifact.kind === 'web' ? '.html' :
      '.txt';

    const blob = new Blob([content], { type: artifact.mimeType || 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${artifact.title.replace(/\s+/g, '-').toLowerCase()}${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const viewportStyle = useMemo(
    () => ({
      transform: `scale(${zoom / 100})`,
      transformOrigin: 'top center',
      width: '100%',
      height: '100%',
      transition: 'transform 0.15s ease'
    }),
    [zoom]
  );

  if (!artifact) return null;

  return (
    <aside
      className={`artifact-panel ${fullscreen ? 'is-fullscreen' : ''}`}
      style={{
        width: fullscreen ? '100vw' : '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--color-bg-secondary, #1e1e2e)',
        borderLeft: '1px solid var(--color-border, rgba(255,255,255,0.1))',
        position: fullscreen ? 'fixed' : 'relative',
        top: fullscreen ? 0 : 'auto',
        left: fullscreen ? 0 : 'auto',
        zIndex: fullscreen ? 9999 : 'auto'
      }}
    >
      {/* Header Toolbar */}
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 16px',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          background: 'var(--color-bg-tertiary, #181825)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0 }}>
          <strong style={{ fontSize: '14px', color: '#f5f5f7', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {artifact.title}
          </strong>
          <span style={{ fontSize: '12px', padding: '2px 8px', borderRadius: '12px', background: 'rgba(99,102,241,0.2)', color: '#818cf8' }}>
            {artifact.kind.toUpperCase()} v{artifact.currentVersion}
          </span>
          {pageCount > 1 && (
            <span style={{ fontSize: '12px', color: '#94a3b8' }}>
              {pageIndex + 1} / {pageCount}
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {pages.length > 1 && (
            <>
              <button
                onClick={() => setPageIndex(Math.max(0, pageIndex - 1))}
                style={{ padding: '4px 8px', borderRadius: '4px', border: 'none', background: 'rgba(255,255,255,0.08)', color: '#fff', cursor: 'pointer' }}
                title="Previous Slide"
              >
                <ChevronLeft size={14} />
              </button>
              <button
                onClick={() => setPageIndex(Math.min(pageCount - 1, pageIndex + 1))}
                style={{ padding: '4px 8px', borderRadius: '4px', border: 'none', background: 'rgba(255,255,255,0.08)', color: '#fff', cursor: 'pointer' }}
                title="Next Slide"
              >
                <ChevronRight size={14} />
              </button>
            </>
          )}

          <button
            onClick={() => setZoom(Math.max(50, zoom - 10))}
            style={{ padding: '4px 8px', borderRadius: '4px', border: 'none', background: 'rgba(255,255,255,0.08)', color: '#fff', cursor: 'pointer' }}
            title="Zoom Out"
          >
            <ZoomOut size={14} />
          </button>
          <span style={{ fontSize: '12px', color: '#94a3b8', width: '36px', textAlign: 'center' }}>{zoom}%</span>
          <button
            onClick={() => setZoom(Math.min(180, zoom + 10))}
            style={{ padding: '4px 8px', borderRadius: '4px', border: 'none', background: 'rgba(255,255,255,0.08)', color: '#fff', cursor: 'pointer' }}
            title="Zoom In"
          >
            <ZoomIn size={14} />
          </button>

          <button
            onClick={handleDownload}
            style={{ padding: '4px 8px', borderRadius: '4px', border: 'none', background: 'rgba(255,255,255,0.08)', color: '#fff', cursor: 'pointer' }}
            title="Download Artifact"
          >
            <Download size={14} />
          </button>

          <button
            onClick={() => setFullscreen((v) => !v)}
            style={{ padding: '4px 8px', borderRadius: '4px', border: 'none', background: 'rgba(255,255,255,0.08)', color: '#fff', cursor: 'pointer' }}
            title="Toggle Fullscreen"
          >
            {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>

          <button
            onClick={() => {
              artifactEvents.emit({ type: 'artifact.close', artifactId: artifact.id, source: 'user' });
              onClose();
            }}
            style={{ padding: '4px 8px', borderRadius: '4px', border: 'none', background: 'rgba(239,68,68,0.2)', color: '#f87171', cursor: 'pointer' }}
            title="Close Panel"
          >
            <X size={14} />
          </button>
        </div>
      </header>

      {/* Body Canvas */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {pages.length > 1 && (
          <nav
            style={{
              width: '112px',
              borderRight: '1px solid rgba(255,255,255,0.1)',
              background: 'var(--color-bg-tertiary, #181825)',
              overflowY: 'auto',
              padding: '8px',
              display: 'flex',
              flexDirection: 'column',
              gap: '8px'
            }}
          >
            {pages.map((p, i) => (
              <button
                key={p.id}
                onClick={() => setPageIndex(i)}
                style={{
                  width: '100%',
                  height: '64px',
                  borderRadius: '6px',
                  border: i === pageIndex ? '2px solid #6366f1' : '1px solid rgba(255,255,255,0.1)',
                  background: i === pageIndex ? 'rgba(99,102,241,0.15)' : 'rgba(255,255,255,0.03)',
                  color: '#fff',
                  cursor: 'pointer',
                  fontSize: '11px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  overflow: 'hidden'
                }}
              >
                {p.thumbnailUrl ? <img src={p.thumbnailUrl} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : <span>Slide {i + 1}</span>}
              </button>
            ))}
          </nav>
        )}

        <main style={{ flex: 1, padding: '16px', overflow: 'auto', display: 'flex', justifyContent: 'center' }}>
          <div style={viewportStyle}>
            <RendererRegistry
              artifact={artifact}
              pageIndex={pageIndex}
              onPageChange={setPageIndex}
            />
          </div>
        </main>
      </div>
    </aside>
  );
};
