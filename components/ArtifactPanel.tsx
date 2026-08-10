import React, { useEffect, useMemo, useState } from 'react';
import { X, ZoomIn, ZoomOut, Download, Maximize2, Minimize2, ChevronLeft, ChevronRight, Eye, Code2 } from 'lucide-react';
import { Artifact } from '../types';
import { RendererRegistry } from '../features/artifacts/RendererRegistry';
import { CodeRenderer } from './artifacts/renderers/CodeRenderer';
import { artifactEvents } from '../lib/artifactEvents';
import { useStore } from '../store/useStore';

interface Props {
  artifact: Artifact | null;
  onClose: () => void;
  onVersionSelect?: (version: number) => void;
}

export const ArtifactPanel: React.FC<Props> = ({ artifact, onClose }) => {
  const { theme } = useStore();
  const isDark = theme === 'dark';

  const [pageIndex, setPageIndex] = useState(0);
  const [zoom, setZoom] = useState(100);
  const [fullscreen, setFullscreen] = useState(false);
  const [viewMode, setViewMode] = useState<'formatted' | 'code'>('formatted');

  useEffect(() => {
    setPageIndex(0);
    setZoom(100);
    setViewMode('formatted');
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

  return (
    <aside
      className={`artifact-panel ${fullscreen ? 'is-fullscreen' : ''}`}
      style={{
        width: fullscreen ? '100vw' : '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--bg-base)',
        color: 'var(--text-primary)',
        borderLeft: '1px solid var(--glass-edge)',
        position: fullscreen ? 'fixed' : 'relative',
        top: fullscreen ? 0 : 'auto',
        left: fullscreen ? 0 : 'auto',
        zIndex: fullscreen ? 9999 : 'auto',
        boxSizing: 'border-box'
      }}
    >
      {/* Header Toolbar */}
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 16px',
          borderBottom: '1px solid var(--glass-edge)',
          background: 'var(--bg-elevated)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0 }}>
          <strong style={{ fontSize: '14px', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {artifact?.title || 'Artifact Workspace'}
          </strong>
          {artifact && (
            <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '12px', background: 'var(--liquid-accent)', color: 'var(--accent)', fontWeight: 600 }}>
              {artifact.kind.toUpperCase()} v{artifact.currentVersion}
            </span>
          )}
          {pageCount > 1 && (
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              {pageIndex + 1} / {pageCount}
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {artifact && (
            <>
              {/* Dual-View Mode Switcher */}
              <button
                onClick={() => setViewMode((m) => (m === 'formatted' ? 'code' : 'formatted'))}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '4px 10px',
                  borderRadius: '6px',
                  border: '1px solid var(--glass-edge)',
                  background: 'var(--liquid-accent)',
                  color: 'var(--accent)',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
                title={viewMode === 'formatted' ? 'Switch to Monaco Code View' : 'Switch to Formatted Document View'}
              >
                {viewMode === 'formatted' ? (
                  <>
                    <Code2 size={13} />
                    <span>Monaco Code</span>
                  </>
                ) : (
                  <>
                    <Eye size={13} />
                    <span>Formatted View</span>
                  </>
                )}
              </button>

              {pages.length > 1 && (
                <>
                  <button
                    onClick={() => setPageIndex(Math.max(0, pageIndex - 1))}
                    style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--glass-edge)', background: 'var(--fill-tertiary)', color: 'var(--text-primary)', cursor: 'pointer' }}
                    title="Previous Slide"
                  >
                    <ChevronLeft size={14} />
                  </button>
                  <button
                    onClick={() => setPageIndex(Math.min(pageCount - 1, pageIndex + 1))}
                    style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--glass-edge)', background: 'var(--fill-tertiary)', color: 'var(--text-primary)', cursor: 'pointer' }}
                    title="Next Slide"
                  >
                    <ChevronRight size={14} />
                  </button>
                </>
              )}

              <button
                onClick={() => setZoom(Math.max(50, zoom - 10))}
                style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--glass-edge)', background: 'var(--fill-tertiary)', color: 'var(--text-primary)', cursor: 'pointer' }}
                title="Zoom Out"
              >
                <ZoomOut size={14} />
              </button>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)', width: '36px', textAlign: 'center' }}>{zoom}%</span>
              <button
                onClick={() => setZoom(Math.min(180, zoom + 10))}
                style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--glass-edge)', background: 'var(--fill-tertiary)', color: 'var(--text-primary)', cursor: 'pointer' }}
                title="Zoom In"
              >
                <ZoomIn size={14} />
              </button>

              <button
                onClick={handleDownload}
                style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--glass-edge)', background: 'var(--fill-tertiary)', color: 'var(--text-primary)', cursor: 'pointer' }}
                title="Download Artifact"
              >
                <Download size={14} />
              </button>

              <button
                onClick={() => setFullscreen((v) => !v)}
                style={{ padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--glass-edge)', background: 'var(--fill-tertiary)', color: 'var(--text-primary)', cursor: 'pointer' }}
                title="Toggle Fullscreen"
              >
                {fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
              </button>
            </>
          )}

          <button
            onClick={() => {
              if (artifact) {
                artifactEvents.emit({ type: 'artifact.close', artifactId: artifact.id, source: 'user' });
              }
              onClose();
            }}
            style={{
              padding: '4px 8px',
              borderRadius: '4px',
              border: '1px solid var(--glass-edge)',
              background: 'var(--fill-tertiary)',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            title="Close Panel"
          >
            <X size={14} />
          </button>
        </div>
      </header>

      {/* Body Canvas */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden', background: 'var(--bg-base)' }}>
        {artifact ? (
          <>
            {pages.length > 1 && (
              <nav
                style={{
                  width: '112px',
                  borderRight: '1px solid var(--glass-edge)',
                  background: 'var(--bg-elevated)',
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
                      border: i === pageIndex ? '2px solid var(--accent)' : '1px solid var(--glass-edge)',
                      background: i === pageIndex ? 'var(--liquid-accent)' : 'transparent',
                      color: 'var(--text-primary)',
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

            <main style={{ flex: 1, padding: '16px', overflow: 'auto', display: 'flex', justifyContent: 'center', background: 'var(--bg-base)' }}>
              <div style={viewportStyle}>
                {viewMode === 'code' ? (
                  <CodeRenderer artifact={artifact} pageIndex={pageIndex} onPageChange={setPageIndex} />
                ) : (
                  <RendererRegistry artifact={artifact} pageIndex={pageIndex} onPageChange={setPageIndex} />
                )}
              </div>
            </main>
          </>
        ) : (
          /* Empty State */
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px', textAlign: 'center', color: 'var(--text-secondary)', background: 'var(--bg-base)' }}>
            <div style={{ fontSize: '16px', fontWeight: 600, marginBottom: '8px', color: 'var(--text-primary)' }}>
              Awaiting Artifact
            </div>
            <div style={{ fontSize: '13px', maxWidth: '320px', lineHeight: '1.5', color: 'var(--text-secondary)' }}>
              When Alluci generates code, presentations, research dossiers, or documents, they will appear here.
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
