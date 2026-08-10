import React, { useMemo, useEffect } from 'react';
import { Artifact } from '../../../types';
import { TextRenderer } from './TextRenderer';
import { ChevronLeft, ChevronRight, Layers, Sparkles, Monitor, ShieldCheck, Cpu, DollarSign } from 'lucide-react';

export interface RendererProps {
  artifact: Artifact;
  pageIndex: number;
  onPageChange: (index: number) => void;
}

interface SlideSection {
  title: string;
  subtitle?: string;
  items: string[];
  metrics?: { label: string; value: string }[];
}

export const PresentationRenderer: React.FC<RendererProps> = ({ artifact, pageIndex, onPageChange }) => {
  const pages = artifact.pages || [];

  // Parse slides and structure sections for PDF-quality rendering
  const parsedSlides = useMemo(() => {
    if (pages.length > 0) {
      return pages.map((p, idx) => ({
        index: idx + 1,
        title: p.title || `Slide ${idx + 1}`,
        eyebrow: 'EXECUTIVE PRESENTATION',
        html: p.html,
        rawContent: p.html,
        sections: [] as SlideSection[]
      }));
    }

    const rawContent = artifact.content || '';
    if (!rawContent) return [];

    // Filter out artifact metadata lines
    const cleanContent = rawContent
      .replace(/^#\s*ARTIFACT:[\s\S]*?(?=---|\n\n##|\n##)/i, '')
      .trim();

    // Split content by '---' slide separators or '## SLIDE' headers
    let slideBlocks = cleanContent.split(/\n(?=---|## SLIDE|## Slide)/g)
      .map(s => s.replace(/^---/g, '').trim())
      .filter(Boolean);

    if (slideBlocks.length <= 1) {
      slideBlocks = cleanContent.split(/\n\n(?=## )/g).map(s => s.trim()).filter(Boolean);
    }

    return slideBlocks.map((block, idx) => {
      const lines = block.split('\n').map(l => l.trim()).filter(Boolean);
      let title = `Slide ${idx + 1}`;
      let eyebrow = 'SOVEREIGN STRATEGY 2026';
      
      const firstLine = lines[0] || '';
      if (firstLine.startsWith('#')) {
        title = firstLine.replace(/^#+\s*(SLIDE\s*\d+:?)?\s*/i, '').trim();
      }

      // Determine category eyebrow badge based on slide title / index
      if (idx === 0) eyebrow = 'STRATEGIC IMPERATIVE';
      else if (title.toLowerCase().includes('spectrum') || title.toLowerCase().includes('utility')) eyebrow = 'CORE PARADIGM SPECTRUM';
      else if (title.toLowerCase().includes('technical') || title.toLowerCase().includes('stack')) eyebrow = 'SOVEREIGN ARCHITECTURE MANDATE';
      else if (title.toLowerCase().includes('financial') || title.toLowerCase().includes('capital') || title.toLowerCase().includes('roadmap')) eyebrow = 'FINANCIAL & CAPITAL HORIZON';

      // Parse sub-sections / grid cards inside the slide
      const sections: SlideSection[] = [];
      let currentSection: SlideSection | null = null;

      lines.slice(1).forEach(line => {
        if (line.startsWith('###') || line.startsWith('**1.') || line.startsWith('**2.') || line.startsWith('**3.') || line.startsWith('**I.') || line.startsWith('**II.') || line.startsWith('**III.') || line.startsWith('**Phase')) {
          if (currentSection) sections.push(currentSection);
          const secTitle = line.replace(/^(###|\*\*[\w\.]+\*\*)\s*/, '').replace(/\*\*/g, '').trim();
          currentSection = { title: secTitle, items: [] };
        } else if (line.startsWith('*') || line.startsWith('-')) {
          const itemText = line.replace(/^[\*\-]\s*/, '').trim();
          if (currentSection) {
            currentSection.items.push(itemText);
          } else {
            if (sections.length === 0) {
              currentSection = { title: 'Core Directives', items: [] };
            }
            currentSection?.items.push(itemText);
          }
        } else if (line.includes(':') && currentSection) {
          currentSection.items.push(line.replace(/\*\*/g, ''));
        }
      });
      if (currentSection) sections.push(currentSection);

      return {
        index: idx + 1,
        title,
        eyebrow,
        html: '',
        rawContent: block,
        sections
      };
    });
  }, [pages, artifact.content]);

  const slideCount = Math.max(parsedSlides.length, 1);
  const currentSlide = parsedSlides[pageIndex] || parsedSlides[0];

  // Enable left / right keyboard arrow navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === 'Space') {
        if (pageIndex < slideCount - 1) onPageChange(pageIndex + 1);
      } else if (e.key === 'ArrowLeft') {
        if (pageIndex > 0) onPageChange(pageIndex - 1);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [pageIndex, slideCount, onPageChange]);

  if (!currentSlide && !artifact.content) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-secondary)' }}>
        No presentation slides available.
      </div>
    );
  }

  const isHtml = currentSlide?.html && currentSlide.html.trim().startsWith('<');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100%', gap: '16px', userSelect: 'none' }}>
      
      {/* Thumbnail Bar */}
      {slideCount > 1 && (
        <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }} className="scrollbar-hide">
          {parsedSlides.map((s, idx) => (
            <button
              key={idx}
              onClick={() => onPageChange(idx)}
              style={{
                flex: 'none',
                padding: '6px 12px',
                borderRadius: '8px',
                border: idx === pageIndex ? '1px solid #10B981' : '1px solid rgba(255,255,255,0.08)',
                background: idx === pageIndex ? 'rgba(16, 185, 129, 0.12)' : 'rgba(255,255,255,0.02)',
                color: idx === pageIndex ? '#10B981' : 'var(--text-tertiary)',
                fontSize: '11px',
                fontFamily: 'monospace',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>0{s.index}</span>
              <span style={{ maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {s.title}
              </span>
            </button>
          ))}
        </div>
      )}

      {/* Main Slide Presentation Stage */}
      <div
        style={{
          flex: 1,
          width: '100%',
          minHeight: '420px',
          background: 'linear-gradient(135deg, #070B12 0%, #0B111E 100%)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '16px',
          overflow: 'auto',
          boxShadow: '0 20px 50px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.1)',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
          padding: '32px'
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
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%', justifyContent: 'space-between' }}>
            
            {/* Header: Eyebrow Tag & Title */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: '#10B981', boxShadow: '0 0 10px #10B981' }} />
                <span style={{ fontSize: '10px', fontFamily: 'monospace', letterSpacing: '0.2em', textTransform: 'uppercase', color: '#10B981', fontWeight: 700 }}>
                  {currentSlide.eyebrow}
                </span>
              </div>
              <h1 style={{ fontSize: '24px', fontWeight: 800, color: '#FFFFFF', letterSpacing: '-0.02em', margin: '0 0 16px 0', lineHeight: 1.2 }}>
                {currentSlide.title}
              </h1>
            </div>

            {/* Slide Body: Structured Glass Cards Grid */}
            <div style={{ flex: 1, margin: '12px 0 24px 0' }}>
              {currentSlide.sections && currentSlide.sections.length > 0 ? (
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: currentSlide.sections.length > 1 ? 'repeat(auto-fit, minmax(260px, 1fr))' : '1fr',
                  gap: '16px'
                }}>
                  {currentSlide.sections.map((sec, sIdx) => (
                    <div
                      key={sIdx}
                      style={{
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        borderRadius: '12px',
                        padding: '18px',
                        backdropFilter: 'blur(12px)',
                        boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '10px'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '8px' }}>
                        <div style={{ fontSize: '11px', fontFamily: 'monospace', fontWeight: 700, color: '#38BDF8', background: 'rgba(56, 189, 248, 0.1)', padding: '2px 6px', borderRadius: '4px' }}>
                          0{sIdx + 1}
                        </div>
                        <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#F3F4F6', margin: 0 }}>
                          {sec.title}
                        </h3>
                      </div>
                      <ul style={{ margin: 0, paddingLeft: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {sec.items.map((item, iIdx) => (
                          <li key={iIdx} style={{ fontSize: '13px', color: '#D1D5DB', lineHeight: '1.5' }}>
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              ) : (
                <TextRenderer
                  artifact={{
                    ...artifact,
                    content: currentSlide.rawContent
                  }}
                  pageIndex={0}
                  onPageChange={() => {}}
                />
              )}
            </div>

            {/* Slide Footer Info */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              borderTop: '1px solid rgba(255, 255, 255, 0.08)',
              paddingTop: '16px',
              fontSize: '10px',
              fontFamily: 'monospace',
              color: 'var(--text-tertiary)'
            }}>
              <span>ALLUCI SOVEREIGN AGENT • TECHNICAL STRATEGY</span>
              <span style={{ color: '#10B981', fontWeight: 700 }}>
                SLIDE 0{pageIndex + 1} / 0{slideCount}
              </span>
            </div>

          </div>
        )}
      </div>

      {/* Navigation Controls Bar */}
      {slideCount > 1 && (
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 0' }}>
          <button
            disabled={pageIndex === 0}
            onClick={() => onPageChange(Math.max(0, pageIndex - 1))}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              background: 'rgba(255, 255, 255, 0.04)',
              color: 'var(--text-primary)',
              cursor: pageIndex === 0 ? 'not-allowed' : 'pointer',
              opacity: pageIndex === 0 ? 0.3 : 1,
              fontSize: '12px',
              fontWeight: 600,
              transition: 'all 0.2s ease'
            }}
          >
            <ChevronLeft size={16} />
            <span>Previous Slide</span>
          </button>

          <span style={{ fontSize: '12px', fontFamily: 'monospace', color: 'var(--text-secondary)', fontWeight: 600 }}>
            {pageIndex + 1} of {slideCount}
          </span>

          <button
            disabled={pageIndex === slideCount - 1}
            onClick={() => onPageChange(Math.min(slideCount - 1, pageIndex + 1))}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              background: pageIndex === slideCount - 1 ? 'rgba(255, 255, 255, 0.04)' : 'rgba(16, 185, 129, 0.15)',
              color: pageIndex === slideCount - 1 ? 'var(--text-primary)' : '#10B981',
              cursor: pageIndex === slideCount - 1 ? 'not-allowed' : 'pointer',
              opacity: pageIndex === slideCount - 1 ? 0.3 : 1,
              fontSize: '12px',
              fontWeight: 600,
              transition: 'all 0.2s ease'
            }}
          >
            <span>Next Slide</span>
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
};
