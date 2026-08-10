import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Artifact } from '../../../types';
import { useStore } from '../../../store/useStore';

export interface RendererProps {
  artifact: Artifact;
  pageIndex: number;
  onPageChange: (index: number) => void;
}

export const TextRenderer: React.FC<RendererProps> = ({ artifact }) => {
  const { theme } = useStore();
  const isDark = theme === 'dark';

  const content = artifact.content || 'Empty text artifact.';

  return (
    <div
      className="markdown-body"
      style={{
        width: '100%',
        height: '100%',
        minHeight: '450px',
        padding: '24px',
        background: isDark ? 'var(--color-bg-tertiary, #181825)' : '#ffffff',
        color: isDark ? 'var(--color-text-primary, #cdd6f4)' : '#1e293b',
        borderRadius: '8px',
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
                borderBottom: isDark ? '1px solid rgba(255,255,255,0.1)' : '1px solid #e2e8f0',
                color: isDark ? '#f5f5f7' : '#0f172a'
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
                color: isDark ? '#e2e8f0' : '#1e293b'
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
                color: isDark ? '#cbd5e1' : '#334155'
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
                  border: isDark ? '1px solid rgba(255,255,255,0.1)' : '1px solid #e2e8f0'
                }}
              >
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead
              style={{
                background: isDark ? 'rgba(99,102,241,0.15)' : '#f1f5f9',
                color: isDark ? '#818cf8' : '#4338ca',
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
                borderBottom: isDark ? '1px solid rgba(255,255,255,0.1)' : '1px solid #e2e8f0'
              }}
            >
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td
              style={{
                padding: '8px 14px',
                borderBottom: isDark ? '1px solid rgba(255,255,255,0.05)' : '1px solid #f1f5f9'
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
                color: '#6366f1',
                textDecoration: 'underline',
                fontWeight: 500
              }}
            >
              {children}
            </a>
          ),
          code: ({ children }) => (
            <code
              style={{
                padding: '2px 6px',
                borderRadius: '4px',
                background: isDark ? 'rgba(255,255,255,0.08)' : '#f1f5f9',
                fontFamily: 'monospace',
                fontSize: '12px',
                color: isDark ? '#f43f5e' : '#e11d48'
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
