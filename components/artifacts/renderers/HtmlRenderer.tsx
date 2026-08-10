import React from 'react';
import { Artifact } from '../../../types';

export interface RendererProps {
  artifact: Artifact;
  pageIndex: number;
  onPageChange: (index: number) => void;
}

export const HtmlRenderer: React.FC<RendererProps> = ({ artifact, pageIndex }) => {
  const page = artifact.pages?.[pageIndex];
  const htmlContent = page?.html || artifact.content || '';

  if (artifact.sourceUri && !htmlContent) {
    return (
      <iframe
        src={artifact.sourceUri}
        title={artifact.title}
        sandbox="allow-scripts"
        style={{
          width: '100%',
          height: '100%',
          minHeight: '450px',
          border: 'none',
          borderRadius: '8px',
          background: '#ffffff'
        }}
      />
    );
  }

  return (
    <iframe
      srcDoc={htmlContent}
      title={artifact.title}
      sandbox="allow-scripts"
      style={{
        width: '100%',
        height: '100%',
        minHeight: '450px',
        border: 'none',
        borderRadius: '8px',
        background: '#ffffff'
      }}
    />
  );
};
