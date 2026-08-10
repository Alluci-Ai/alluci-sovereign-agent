import React from 'react';
import { Artifact } from '../../types';
import { CodeRenderer } from '../../components/artifacts/renderers/CodeRenderer';
import { HtmlRenderer } from '../../components/artifacts/renderers/HtmlRenderer';
import { PresentationRenderer } from '../../components/artifacts/renderers/PresentationRenderer';
import { TextRenderer } from '../../components/artifacts/renderers/TextRenderer';

export interface RendererProps {
  artifact: Artifact;
  pageIndex: number;
  onPageChange: (index: number) => void;
  previousVersionContent?: string;
}

export const RendererRegistry: React.FC<RendererProps> = (props) => {
  switch (props.artifact.kind) {
    case 'code':
      return <CodeRenderer {...props} />;
    case 'html':
    case 'web':
      return <HtmlRenderer {...props} />;
    case 'presentation':
      return <PresentationRenderer {...props} />;
    case 'text':
    default:
      return <TextRenderer {...props} />;
  }
};
