import React, { useState } from 'react';
import Editor, { DiffEditor } from '@monaco-editor/react';
import { Artifact } from '../../../types';
import { useStore } from '../../../store/useStore';

export interface RendererProps {
  artifact: Artifact;
  pageIndex: number;
  onPageChange: (index: number) => void;
  previousVersionContent?: string;
}

export const CodeRenderer: React.FC<RendererProps> = ({ artifact, previousVersionContent }) => {
  const { theme } = useStore();
  const [showDiff, setShowDiff] = useState(false);

  const monacoTheme = theme === 'dark' ? 'vs-dark' : 'vs';
  const language = (artifact.metadata?.language || 'typescript').toLowerCase();
  const content = artifact.content || '';

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', minHeight: '450px' }}>
      {previousVersionContent && (
        <div style={{ padding: '6px 12px', background: 'var(--color-bg-secondary, #1e1e2e)', display: 'flex', justifyContent: 'flex-end', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
          <button
            onClick={() => setShowDiff((v) => !v)}
            style={{
              padding: '4px 10px',
              fontSize: '12px',
              borderRadius: '4px',
              border: 'none',
              background: showDiff ? '#6366f1' : 'rgba(255,255,255,0.1)',
              color: '#fff',
              cursor: 'pointer'
            }}
          >
            {showDiff ? 'Exit Diff View' : 'Compare with Previous Version'}
          </button>
        </div>
      )}

      <div style={{ flex: 1, minHeight: '400px' }}>
        {showDiff && previousVersionContent ? (
          <DiffEditor
            height="100%"
            language={language}
            original={previousVersionContent}
            modified={content}
            theme={monacoTheme}
            options={{
              readOnly: true,
              minimap: { enabled: false },
              fontSize: 13,
              scrollBeyondLastLine: false,
              automaticLayout: true
            }}
          />
        ) : (
          <Editor
            height="100%"
            language={language}
            value={content}
            theme={monacoTheme}
            options={{
              readOnly: true,
              minimap: { enabled: true },
              fontSize: 13,
              lineNumbers: 'on',
              scrollBeyondLastLine: false,
              automaticLayout: true,
              wordWrap: 'on'
            }}
          />
        )}
      </div>
    </div>
  );
};
