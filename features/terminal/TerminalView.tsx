import React, { useRef, useEffect } from 'react';
import { useStore } from '../../store/useStore';
import { ExecutionTimeline } from '../../components/Visualizers';
import PolytopeIdentity from '../../components/Identity';
import { JumpToNewButton } from '../chat/JumpToNewButton';
import { ReadingIndicator } from '../chat/ReadingIndicator';
import { CopyMessageButton } from '../chat/CopyMessageButton';
import { SourceAttribution } from '../chat/SourceAttribution';
import mermaid from 'mermaid';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';

// Initialize mermaid configurations
if (typeof window !== 'undefined') {
    mermaid.initialize({
        startOnLoad: false,
        theme: 'dark',
        securityLevel: 'loose',
        suppressErrorAlerts: true,
        suppressErrorRendering: true
    } as any);

    // Safeguard to prevent Mermaid from appending default syntax error overlays/bombs to body
    (mermaid as any).parseError = (err: any) => {
        // Just throw the error so our try-catch block handles it without DOM pollution
        throw new Error(err);
    };
}

interface TerminalViewProps {
    getFormattedTime: (iso: string) => string;
    copyText: (text: string) => void;
}

interface MermaidProps {
    chart: string;
}

const Mermaid: React.FC<MermaidProps> = ({ chart }) => {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const [svg, setSvg] = React.useState<string>('');
    const [error, setError] = React.useState<string | null>(null);
    const [isExpanded, setIsExpanded] = React.useState<boolean>(false);

    useEffect(() => {
        let isMounted = true;
        const renderDiagram = async () => {
            if (!chart) return;
            const uniqueId = `mermaid-${Math.random().toString(36).substring(2, 9)}`;
            
            // Clean common comment syntax issues (e.g. LLM outputting '//' comments instead of '%%')
            const cleanedChart = chart
                .split('\n')
                .map(line => {
                    const commentIndex = line.indexOf('//');
                    if (commentIndex !== -1) {
                        const isUrl = /https?:\/\//.test(line);
                        if (!isUrl) {
                            return line.substring(0, commentIndex) + '%%' + line.substring(commentIndex + 2);
                        }
                    }
                    return line;
                })
                .join('\n');

            try {
                const { svg: renderedSvg } = await mermaid.render(uniqueId, cleanedChart);
                if (isMounted) {
                    setSvg(renderedSvg);
                    setError(null);
                }
            } catch (err: any) {
                console.error('Mermaid render error:', err);
                if (isMounted) {
                    setError(err?.message || String(err));
                }
            }
        };

        renderDiagram();

        return () => {
            isMounted = false;
        };
    }, [chart]);

    if (error) {
        return (
            <div className="my-4 p-3 border border-red-500/20 bg-red-500/10 text-red-400 rounded text-xs font-mono whitespace-pre-wrap">
                <div>Mermaid Error:</div>
                <div>{error}</div>
                <pre className="mt-2 text-[10px] text-gray-400">{chart}</pre>
            </div>
        );
    }

    if (!svg) {
        return (
            <div className="my-4 p-4 flex items-center justify-center border border-white/5 bg-black/10 rounded min-h-[100px] text-xs text-text-tertiary font-mono animate-pulse">
                Rendering diagram...
            </div>
        );
    }

    return (
        <>
            <div 
                ref={containerRef}
                onClick={() => setIsExpanded(true)}
                className="my-4 p-4 border border-white/10 bg-black/30 rounded-lg overflow-x-auto flex justify-center w-full mermaid-diagram cursor-pointer hover:border-white/20 transition-all hover:bg-black/40"
                dangerouslySetInnerHTML={{ __html: svg }}
                title="Click to expand diagram view"
                data-testid="mermaid-clickable-diagram"
            />
            {isExpanded && (
                <div 
                    className="glass-sheet-backdrop animate-fade-in"
                    onClick={() => setIsExpanded(false)}
                    data-testid="mermaid-modal-backdrop"
                >
                    <div 
                        className="glass-sheet max-w-7xl w-[92vw] h-[85vh] p-6 flex flex-col relative"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="absolute top-4 right-4 z-[10001]">
                            <button
                                onClick={() => setIsExpanded(false)}
                                className="text-gray-400 hover:text-white transition-colors bg-white/5 hover:bg-white/10 p-2 rounded-full cursor-pointer flex items-center justify-center w-8 h-8 font-bold font-mono border-0"
                                title="Close"
                                data-testid="mermaid-modal-close"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="w-full text-center pb-4 mb-4 border-b border-white/10 flex-shrink-0">
                            <h3 className="text-xs font-bold text-text-primary uppercase tracking-wider font-mono">
                                Expanded Diagram View
                            </h3>
                            <p className="text-[10px] text-text-tertiary mt-1">
                                Drag to pan • Scroll or Pinch to zoom • Tap ✕ or click outside to close
                            </p>
                        </div>

                        <TransformWrapper
                            initialScale={1}
                            minScale={0.1}
                            maxScale={8}
                            centerOnInit={true}
                        >
                            {({ zoomIn, zoomOut, resetTransform }) => (
                                <>
                                    {/* Glassmorphic zoom controls */}
                                    <div className="absolute bottom-6 left-6 z-[10001] flex gap-2">
                                        <button
                                            onClick={() => zoomIn()}
                                            className="text-xs bg-black/60 hover:bg-black/80 text-text-primary px-3 py-2 rounded-lg border border-white/10 flex items-center justify-center font-mono font-bold transition-all shadow-lg hover:border-white/20 active:scale-95 cursor-pointer"
                                            title="Zoom In"
                                            data-testid="mermaid-zoom-in"
                                        >
                                            ＋ Zoom In
                                        </button>
                                        <button
                                            onClick={() => zoomOut()}
                                            className="text-xs bg-black/60 hover:bg-black/80 text-text-primary px-3 py-2 rounded-lg border border-white/10 flex items-center justify-center font-mono font-bold transition-all shadow-lg hover:border-white/20 active:scale-95 cursor-pointer"
                                            title="Zoom Out"
                                            data-testid="mermaid-zoom-out"
                                        >
                                            － Zoom Out
                                        </button>
                                        <button
                                            onClick={() => resetTransform()}
                                            className="text-xs bg-black/60 hover:bg-black/80 text-text-primary px-3 py-2 rounded-lg border border-white/10 flex items-center justify-center font-mono font-bold transition-all shadow-lg hover:border-white/20 active:scale-95 cursor-pointer"
                                            title="Reset View"
                                            data-testid="mermaid-zoom-reset"
                                        >
                                            ⟲ Reset
                                        </button>
                                    </div>
                                    
                                    <div className="flex-1 w-full overflow-hidden flex justify-center items-center bg-black/20 rounded-lg border border-white/5 relative">
                                        <TransformComponent
                                            wrapperStyle={{ width: '100%', height: '100%' }}
                                            contentStyle={{ width: '100%', height: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}
                                        >
                                            <div 
                                                className="mermaid-expanded-diagram p-8 cursor-grab active:cursor-grabbing select-none flex items-center justify-center"
                                                dangerouslySetInnerHTML={{ __html: svg }}
                                            />
                                        </TransformComponent>
                                    </div>
                                </>
                            )}
                        </TransformWrapper>
                    </div>
                </div>
            )}
        </>
    );
};

const renderMarkdown = (text: string) => {
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];
    let inList = false;
    let listItems: React.ReactNode[] = [];
    let inTable = false;
    let tableRows: string[][] = [];
    let inCodeBlock = false;
    let codeBlockContent: string[] = [];
    let codeBlockLang = '';

    const flushList = (key: string | number) => {
        if (listItems.length > 0) {
            elements.push(
                <ul key={`list-${key}`} className="list-disc pl-6 my-2 space-y-1">
                    {listItems}
                </ul>
            );
            listItems = [];
        }
        inList = false;
    };

    const flushTable = (key: string | number) => {
        if (tableRows.length > 0) {
            let headers: string[] = [];
            let rows: string[][] = [];
            
            if (tableRows.length > 1 && tableRows[1].every(cell => /^:?-+:?$/.test(cell.trim()))) {
                headers = tableRows[0];
                rows = tableRows.slice(2);
            } else {
                rows = tableRows;
            }

            elements.push(
                <div key={`table-wrapper-${key}`} className="overflow-x-auto my-4 border border-[rgba(255,255,255,0.1)] rounded-lg w-full">
                    <table className="min-w-full divide-y divide-[rgba(255,255,255,0.1)] bg-[rgba(255,255,255,0.02)]">
                        {headers.length > 0 && (
                            <thead className="bg-[rgba(255,255,255,0.05)]">
                                <tr>
                                    {headers.map((h, idx) => (
                                        <th key={idx} className="px-4 py-2 text-left text-xs font-bold text-text-secondary uppercase tracking-wider">
                                            {parseInlineMarkdown(h)}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                        )}
                        <tbody className="divide-y divide-[rgba(255,255,255,0.05)]">
                            {rows.map((row, rIdx) => (
                                <tr key={rIdx} className="hover:bg-[rgba(255,255,255,0.01)] transition-colors">
                                    {row.map((cell, cIdx) => (
                                        <td key={cIdx} className="px-4 py-2 text-sm text-text-primary">
                                            {parseInlineMarkdown(cell)}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            );
            tableRows = [];
        }
        inTable = false;
    };

    const flushCodeBlock = (key: string | number, isComplete: boolean) => {
        if (inCodeBlock) {
            const codeText = codeBlockContent.join('\n');
            if (codeBlockLang === 'mermaid' && isComplete) {
                elements.push(<Mermaid key={`mermaid-${key}`} chart={codeText} />);
            } else {
                elements.push(
                    <pre key={`code-${key}`} className="font-mono text-xs bg-black/30 border border-white/10 rounded p-3 my-2 overflow-x-auto whitespace-pre">
                        <code className="text-text-primary">{codeText}</code>
                        {codeBlockLang === 'mermaid' && (
                            <div className="text-[10px] text-accent animate-pulse mt-2 font-sans flex items-center gap-1.5">
                                <span>⚒</span> Rendering diagram layout...
                            </div>
                        )}
                    </pre>
                );
            }
            codeBlockContent = [];
            inCodeBlock = false;
            codeBlockLang = '';
        }
    };

    const parseInlineMarkdown = (inlineText: string): React.ReactNode => {
        const parts = inlineText.split(/(\*\*.*?\*\*|\*.*?\*)/);
        return parts.map((part, index) => {
            if (part.startsWith('**') && part.endsWith('**')) {
                return <strong key={index} className="font-extrabold text-white">{part.slice(2, -2)}</strong>;
            }
            if (part.startsWith('*') && part.endsWith('*')) {
                return <em key={index} className="italic text-text-secondary">{part.slice(1, -1)}</em>;
            }
            return part;
        });
    };

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const trimmed = line.trim();

        // 0. Handle Code Blocks
        if (inCodeBlock) {
            if (trimmed.startsWith('```')) {
                flushCodeBlock(i, true);
            } else {
                codeBlockContent.push(line);
            }
            continue;
        }

        if (trimmed.startsWith('```')) {
            if (inList) flushList(i);
            if (inTable) flushTable(i);
            inCodeBlock = true;
            codeBlockLang = trimmed.slice(3).trim().toLowerCase();
            codeBlockContent = [];
            continue;
        }

        // 1. Handle Table Rows
        if (trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.length > 1) {
            if (inList) flushList(i);
            inTable = true;
            const cells = trimmed.split('|').map(c => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
            tableRows.push(cells);
            continue;
        } else if (inTable) {
            flushTable(i);
        }

        // 2. Handle List Items
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('o ')) {
            if (inTable) flushTable(i);
            inList = true;
            const content = trimmed.replace(/^[-*o]\s+/, '');
            listItems.push(
                <li key={`li-${i}`} className="text-sm leading-relaxed text-text-primary">
                    {parseInlineMarkdown(content)}
                </li>
            );
            continue;
        } else if (inList) {
            flushList(i);
        }

        // 3. Handle Headers
        if (trimmed.startsWith('#')) {
            const match = trimmed.match(/^(#{1,6})\s*(.*)$/);
            if (match) {
                const level = match[1].length;
                const headerText = match[2];
                const headerClass = level === 1 
                    ? "text-2xl font-black text-white mt-6 mb-3 tracking-wide" 
                    : level === 2 
                    ? "text-xl font-bold text-white mt-5 mb-2.5 tracking-wide" 
                    : "text-lg font-semibold text-white mt-4 mb-2 tracking-wide";
                
                const HeaderTag = `h${level}` as any;
                elements.push(
                    <div key={`h-wrap-${i}`} className="py-2">
                        <HeaderTag className={headerClass}>
                            {parseInlineMarkdown(headerText)}
                        </HeaderTag>
                    </div>
                );
                continue;
            }
        }

        // 4. Handle Blank Lines
        if (trimmed === '') {
            elements.push(<div key={`blank-${i}`} className="h-3 shrink-0" />);
            continue;
        }

        // 5. Normal Paragraphs
        elements.push(
            <p key={`p-${i}`} className="text-sm leading-relaxed text-text-primary mb-2">
                {parseInlineMarkdown(line)}
            </p>
        );
    }

    if (inList) flushList('final');
    if (inTable) flushTable('final');
    if (inCodeBlock) flushCodeBlock('final', false);

    return <div className="flex flex-col w-full text-left">{elements}</div>;
};

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const TerminalView: React.FC<TerminalViewProps> = ({ getFormattedTime, copyText }) => {
    const { transcriptions, isProcessing } = useStore();
    const messagesEndRef = useRef<HTMLDivElement | null>(null);
    const scrollContainerRef = useRef<HTMLDivElement | null>(null);
    const [viewMode, setViewMode] = React.useState<'chat' | 'dispatch'>('chat');

    const filteredTranscriptions = transcriptions.filter(t => 
        viewMode === 'dispatch' ? t.type === 'dispatch' : (t.type !== 'dispatch')
    );

    const lastMessage = filteredTranscriptions[filteredTranscriptions.length - 1];
    const showReadingIndicator = isProcessing && (!lastMessage || lastMessage.isUser || !lastMessage.text || lastMessage.text.trim() === '');

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [filteredTranscriptions.length, isProcessing, viewMode]);

    return (
        <div className="flex-1 flex flex-col h-full overflow-hidden bg-transparent relative">
            <div className="flex justify-between items-center border-b border-[rgba(255,255,255,0.08)] bg-glass-1 backdrop-blur-md px-4 shrink-0">
                <div className="flex">
                    <button 
                        onClick={() => setViewMode('chat')}
                        className={`px-4 py-3 text-[10px] font-bold tracking-widest uppercase transition-colors ${viewMode === 'chat' ? 'text-accent border-b-2 border-accent' : 'text-text-tertiary hover:text-text-secondary'}`}
                    >
                        Chat History
                    </button>
                    <button 
                        onClick={() => setViewMode('dispatch')}
                        className={`px-4 py-3 text-[10px] font-bold tracking-widest uppercase transition-colors ${viewMode === 'dispatch' ? 'text-accent-warm border-b-2 border-accent-warm' : 'text-text-tertiary hover:text-text-secondary'}`}
                    >
                        Dispatch Logs
                    </button>
                </div>
                {filteredTranscriptions.length > 0 && (
                    <div className="pr-2 flex items-center">
                        <JumpToNewButton
                            scrollContainerRef={scrollContainerRef}
                            messagesEndRef={messagesEndRef}
                        />
                    </div>
                )}
            </div>
            
            <div ref={scrollContainerRef} className="flex-1 overflow-y-auto p-4 md:p-8 flex flex-col gap-6 md:gap-8 scrollbar-hide relative bg-transparent">
                <ExecutionTimeline isProcessing={isProcessing} />
                {filteredTranscriptions.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center opacity-5 select-none animate-pulse">
                        <PolytopeIdentity color="#000" size={100} />
                        <h2 className="glass-label text-[8px] mt-6 tracking-[1.2em]">
                            {viewMode === 'chat' ? 'EXECUTIVE_SESSION_IDLE' : 'NO_DISPATCH_LOGS_YET'}
                        </h2>
                    </div>
                )}
                {filteredTranscriptions.map((t, i) => {
                    const showCompaction = t.isCompaction;
                    const showMessage = t.text && t.text.trim() !== '';

                    if (!showCompaction && !showMessage) return null;

                    return (
                        <div key={i} className="flex flex-col gap-4">
                            {/* Context Compaction Divider — shows token count when available */}
                            {showCompaction && (
                                <div className="compaction-divider" role="separator" aria-label="Context compaction event">
                                    <div className="flex items-center gap-4 py-8 animate-in fade-in duration-700">
                                        <div className="flex-1 h-[1px] bg-gradient-to-r from-transparent via-glass-edge to-transparent opacity-20" />
                                        <div className="flex flex-col items-center gap-2">
                                            <div className="text-[10px] glass-label text-text-tertiary tracking-[0.4em] uppercase">Context Manifold Compacted</div>
                                            {t.tokenCount != null && t.tokenCount > 0 && (
                                                <div className="text-[9px] font-mono text-accent opacity-70">
                                                    {t.tokenCount.toLocaleString()} tokens freed
                                                </div>
                                            )}
                                            <div className="text-[8px] font-mono text-text-quaternary opacity-40">PRIOR_HISTORY_ANCHORED_TO_VAULT</div>
                                        </div>
                                        <div className="flex-1 h-[1px] bg-gradient-to-r from-glass-edge via-glass-edge to-transparent opacity-20" />
                                    </div>
                                </div>
                            )}
                            {showMessage && (
                                <div className={`flex flex-col ${t.isUser ? 'items-end' : 'items-start'} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
                                    <div className="flex items-center gap-2 mb-1.5 opacity-60">
                                        <span className="text-[9px] glass-label text-text-secondary tracking-widest">{t.isUser ? 'USER' : 'ALLUCI'}</span>
                                        <span className="text-[8px] font-mono text-text-tertiary">[{getFormattedTime(t.timestamp)}]</span>
                                    </div>
                                    <div className={`relative group max-w-[85%] md:max-w-[70%] px-5 py-3.5 text-[14px] leading-relaxed shadow-lg backdrop-blur-xl ${t.isUser ? 'bg-[rgba(0,113,227,0.18)] border border-[rgba(0,113,227,0.30)] text-text-primary rounded-[20px] rounded-br-[4px]' : 'bg-glass-2 border border-glass-edge text-text-primary rounded-[20px] rounded-bl-[4px]'}`}>
                                        {renderMarkdown(t.text)}
                                        <CopyMessageButton text={t.text} />

                                        {!t.isUser && (
                                            <SourceAttribution modelName={t.modelName} tokenCount={t.tokenCount} />
                                        )}

                                        {t.sources && t.sources.length > 0 && (
                                            <div className="mt-4 pt-4 border-t border-[rgba(255,255,255,0.1)] flex flex-wrap gap-2">
                                                <span className="glass-label text-[8px] text-text-secondary w-full mb-1">GROUNDING_CONTEXT</span>
                                                {t.sources.map((s, idx) => (
                                                    <a key={idx} href={s.uri} target="_blank" rel="noopener noreferrer" className="text-[10px] bg-glass-pressed hover:bg-glass-hover text-text-primary rounded-md px-3 py-1.5 border border-glass-edge no-underline transition-all">
                                                        {s.title.slice(0, 20)}...
                                                    </a>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            {showReadingIndicator && <ReadingIndicator />}
            <div ref={messagesEndRef} className="h-4 flex-none" />
            </div>
        </div>
    );
};

export default TerminalView;
