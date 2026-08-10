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
        background: isDark ? 'var(--color-bg-secondary, #1e1e2e)' : '#f8fafc',
        color: isDark ? '#f5f5f7' : '#0f172a',
        borderLeft: isDark ? '1px solid rgba(255,255,255,0.1)' : '1px solid #e2e8f0',
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
          borderBottom: isDark ? '1px solid rgba(255,255,255,0.1)' : '1px solid #e2e8f0',
          background: isDark ? 'var(--color-bg-tertiary, #181825)' : '#ffffff'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0 }}>
          <strong style={{ fontSize: '14px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {artifact?.title || 'Artifact Workspace'}
          </strong>
          {artifact && (
            <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '12px', background: isDark ? 'rgba(99,102,241,0.2)' : '#e0e7ff', color: isDark ? '#818cf8' : '#4338ca' }}>
              {artifact.kind.toUpperCase()} v{artifact.currentVersion}
            </span>
          )}
          {pageCount > 1 && (
            <span style={{ fontSize: '12px', color: isDark ? '#94a3b8' : '#64748b' }}>
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
                  border: 'none',
                  background: isDark ? 'rgba(99,102,241,0.2)' : '#e0e7ff',
                  color: isDark ? '#818cf8' : '#4338ca',
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
                    style={{ padding: '4px 8px', borderRadius: '4px', border: 'none', background: isDark ? 'rgba(255,255,255,0.08)' : '#e2e8f0', color: isDark ? '#fff' : '#1e293b', cursor: 'pointer' }}
                    title="Previous Slide"
                  >
                    <ChevronLeft size={14} />
                  </button>
                  <button
                    onClick={() => setPageIndex(Math.min(pageCount - 1, pageIndex + 1))}
                    style={{ padding: '4px 8px', borderRadius: '4px', border: 'none', background: isDark ? 'rgba(255,255,255,0.08)' : '#e2e8f0', color: isDark ? '#fff' : '#1e293b', cursor: 'pointer' }}
                    title="Next Slide"
                  >
                    <ChevronRight size={14} />
                  </button>
                </>
              )}

              <button
                onClick={() => setZoom(Math.max(50, zoom - 10))}
                style={{ padding: '4px 8px', borderRadius: '4px', border: 'none', background: isDark ? 'rgba(255,255,255,0.08)' : '#e2e8f0', color: isDark ? '#fff' : '#1e293b', cursor: 'pointer' }}
                title="Zoom Out"
              >
                <ZoomOut size={14} />
              </button>
              <span style={{ fontSize: '12px', color: isDark ? '#94a3b8' : '#64748b', width: '36px', textAlign: 'center' }}>{zoom}%</span>
              <button
                onClick={() => setZoom(Math.min(180, zoom + 10))}
                style={{ padding: '4px 8px', borderRadius: '4px', border: 'none', background: isDark ? 'rgba(255,255,255,0.08)' : '#e2e8f0', color: isDark ? '#fff' : '#1e293b', cursor: 'pointer' }}
                title="Zoom In"
              >
                <ZoomIn size={14} />
              </button>

              <button
                onClick={handleDownload}
                style={{ padding: '4px 8px', borderRadius: '4px', border: 'none', background: isDark ? 'rgba(255,255,255,0.08)' : '#e2e8f0', color: isDark ? '#fff' : '#1e293b', cursor: 'pointer' }}
                title="Download Artifact"
              >
                <Download size={14} />
              </button>

              <button
                onClick={() => setFullscreen((v) => !v)}
                style={{ padding: '4px 8px', borderRadius: '4px', border: 'none', background: isDark ? 'rgba(255,255,255,0.08)' : '#e2e8f0', color: isDark ? '#fff' : '#1e293b', cursor: 'pointer' }}
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
            style={{ padding: '4px 8px', borderRadius: '4px', border: 'none', background: 'rgba(239,68,68,0.2)', color: '#f87171', cursor: 'pointer' }}
            title="Close Panel"
          >
            <X size={14} />
          </button>
        </div>
      </header>

      {/* Body Canvas */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {artifact ? (
          <>
            {pages.length > 1 && (
              <nav
                style={{
                  width: '112px',
                  borderRight: isDark ? '1px solid rgba(255,255,255,0.1)' : '1px solid #e2e8f0',
                  background: isDark ? 'var(--color-bg-tertiary, #181825)' : '#f1f5f9',
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
                      border: i === pageIndex ? '2px solid #6366f1' : isDark ? '1px solid rgba(255,255,255,0.1)' : '1px solid #cbd5e1',
                      background: i === pageIndex ? 'rgba(99,102,241,0.15)' : 'transparent',
                      color: isDark ? '#fff' : '#0f172a',
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
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px', textAlign: 'center', color: isDark ? '#94a3b8' : '#64748b' }}>
            <div style={{ fontSize: '16px', fontWeight: 600, marginBottom: '8px', color: isDark ? '#f5f5f7' : '#0f172a' }}>
              Awaiting Artifact
            </div>
            <div style={{ fontSize: '13px', maxWidth: '320px', lineHeight: '1.5' }}>
              When Alluci generates code, presentations, research dossiers, or documents, they will appear here.
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
