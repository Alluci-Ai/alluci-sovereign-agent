import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Artifact } from '../../../types';

export interface RendererProps {
  artifact: Artifact;
  pageIndex: number;
  onPageChange: (index: number) => void;
}

export const TextRenderer: React.FC<RendererProps> = ({ artifact }) => {
  const content = artifact.content || 'Empty text artifact.';

  return (
    <div
      className="markdown-body"
      style={{
        width: '100%',
        height: '100%',
        minHeight: '450px',
        padding: '24px',
        background: 'var(--bg-elevated)',
        color: 'var(--text-primary)',
        borderRadius: '8px',
        border: '1px solid var(--glass-edge)',
        fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        fontSize: '14px',
        lineHeight: '1.65',
        overflowY: 'auto',
        boxSizing: 'border-box'
      }}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1
              style={{
                fontSize: '22px',
                fontWeight: 700,
                marginBottom: '16px',
                paddingBottom: '8px',
                borderBottom: '1px solid var(--glass-edge)',
                color: 'var(--text-primary)'
              }}
            >
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2
              style={{
                fontSize: '18px',
                fontWeight: 600,
                marginTop: '20px',
                marginBottom: '12px',
                color: 'var(--text-primary)'
              }}
            >
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3
              style={{
                fontSize: '15px',
                fontWeight: 600,
                marginTop: '16px',
                marginBottom: '8px',
                color: 'var(--text-secondary)'
              }}
            >
              {children}
            </h3>
          ),
          table: ({ children }) => (
            <div style={{ overflowX: 'auto', margin: '16px 0' }}>
              <table
                style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  fontSize: '13px',
                  borderRadius: '6px',
                  overflow: 'hidden',
                  border: '1px solid var(--glass-edge)'
                }}
              >
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead
              style={{
                background: 'var(--fill-tertiary)',
                color: 'var(--text-primary)',
                fontWeight: 600
              }}
            >
              {children}
            </thead>
          ),
          th: ({ children }) => (
            <th
              style={{
                padding: '10px 14px',
                textAlign: 'left',
                borderBottom: '1px solid var(--glass-edge)'
              }}
            >
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td
              style={{
                padding: '8px 14px',
                borderBottom: '1px solid var(--glass-edge)'
              }}
            >
              {children}
            </td>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: 'var(--accent, #30D158)',
                textDecoration: 'underline',
                fontWeight: 500,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              {children}
            </a>
          ),
          img: ({ src, alt }) => {
            const cleanSrc = src && !src.startsWith('http') && !src.startsWith('/') ? `/${src}` : src;
            const docSlugMatch = cleanSrc ? cleanSrc.match(/\/extracted_figures\/([^\/]+)\/([^\/\?#]+)/) : null;
            const localDiskPath = docSlugMatch ? `workspace/artifacts/extracted_figures/${docSlugMatch[1]}/${docSlugMatch[2]}` : (cleanSrc || '');

            return (
              <div 
                style={{ 
                  margin: '24px 0', 
                  padding: '16px',
                  background: 'var(--glass-2, rgba(255, 255, 255, 0.03))',
                  borderRadius: '12px',
                  border: '1px solid var(--glass-edge, rgba(255, 255, 255, 0.08))',
                  textAlign: 'center' 
                }}
              >
                <div style={{ position: 'relative', overflow: 'hidden', borderRadius: '8px', background: 'rgba(0,0,0,0.4)', minHeight: '120px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <img
                    src={cleanSrc}
                    alt={alt || 'Technical Visual Asset'}
                    style={{
                      maxWidth: '100%',
                      height: 'auto',
                      maxHeight: '600px',
                      borderRadius: '8px',
                      objectFit: 'contain',
                      boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
                      cursor: 'zoom-in'
                    }}
                    loading="lazy"
                    onClick={() => {
                      if (cleanSrc) window.open(cleanSrc, '_blank');
                    }}
                  />
                </div>
                {alt && (
                  <p
                    style={{
                      fontSize: '13px',
                      color: 'var(--text-secondary)',
                      marginTop: '10px',
                      fontStyle: 'italic',
                      lineHeight: '1.4'
                    }}
                  >
                    {alt}
                  </p>
                )}
                <div 
                  style={{
                    marginTop: '12px',
                    paddingTop: '8px',
                    borderTop: '1px solid var(--glass-edge, rgba(255, 255, 255, 0.08))',
                    display: 'flex',
                    flexWrap: 'wrap',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '8px',
                    fontSize: '11px',
                    fontFamily: 'monospace'
                  }}
                >
                  <a
                    href={cleanSrc}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      color: 'var(--accent, #30D158)',
                      textDecoration: 'none',
                      fontWeight: 600,
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <span>🔍 View High-Resolution Diagram</span>
                  </a>
                  <button
                    onClick={() => {
                      if (navigator.clipboard && localDiskPath) {
                        navigator.clipboard.writeText(localDiskPath);
                      }
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-tertiary, #94a3b8)',
                      cursor: 'pointer',
                      fontSize: '11px',
                      fontFamily: 'monospace',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                    title={`Click to copy local path: ${localDiskPath}`}
                  >
                    <span>📁 Local File: {localDiskPath.split('/').pop()}</span>
                  </button>
                </div>
              </div>
            );
          },
          code: ({ children }) => (
            <code
              style={{
                padding: '2px 6px',
                borderRadius: '4px',
                background: 'var(--fill-tertiary)',
                fontFamily: 'monospace',
                fontSize: '12px',
                color: 'var(--text-primary)'
              }}
            >
              {children}
            </code>
          )
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
