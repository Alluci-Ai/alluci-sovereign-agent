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
                fontWeight: 500
              }}
            >
              {children}
            </a>
          ),
          img: ({ src, alt }) => {
            const cleanSrc = src && !src.startsWith('http') && !src.startsWith('/') ? `/${src}` : src;
            return (
              <div style={{ margin: '20px 0', textAlign: 'center' }}>
                <img
                  src={cleanSrc}
                  alt={alt || 'Technical Visual Asset'}
                  style={{
                    maxWidth: '100%',
                    height: 'auto',
                    borderRadius: '8px',
                    border: '1px solid var(--glass-edge)',
                    boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
                    objectFit: 'contain',
                    maxHeight: '600px'
                  }}
                  loading="lazy"
                />
                {alt && (
                  <p
                    style={{
                      fontSize: '12px',
                      color: 'var(--text-secondary)',
                      marginTop: '8px',
                      fontStyle: 'italic'
                    }}
                  >
                    {alt}
                  </p>
                )}
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
