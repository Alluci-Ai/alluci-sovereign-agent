import React, { useRef, useEffect } from 'react';
import { useStore } from '../../store/useStore';
import { ExecutionTimeline } from '../../components/Visualizers';
import PolytopeIdentity from '../../components/Identity';
import { JumpToNewButton } from '../chat/JumpToNewButton';
import { ReadingIndicator } from '../chat/ReadingIndicator';
import { CopyMessageButton } from '../chat/CopyMessageButton';
import { SourceAttribution } from '../chat/SourceAttribution';

interface TerminalViewProps {
    getFormattedTime: (iso: string) => string;
    copyText: (text: string) => void;
}

const TerminalView: React.FC<TerminalViewProps> = ({ getFormattedTime, copyText }) => {
    const { transcriptions, isProcessing } = useStore();
    const messagesEndRef = useRef<HTMLDivElement | null>(null);
    const scrollContainerRef = useRef<HTMLDivElement | null>(null);
    const [viewMode, setViewMode] = React.useState<'chat' | 'dispatch'>('chat');

    const filteredTranscriptions = transcriptions.filter(t => 
        viewMode === 'dispatch' ? t.type === 'dispatch' : (t.type !== 'dispatch')
    );

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [filteredTranscriptions.length, isProcessing, viewMode]);

    return (
        <div className="flex-1 flex flex-col h-full overflow-hidden bg-transparent relative">
            <div className="flex border-b border-[rgba(255,255,255,0.08)] bg-glass-1 backdrop-blur-md px-4 shrink-0">
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
                {filteredTranscriptions.map((t, i) => (
                <div key={i} className="flex flex-col gap-4">
                    {/* Context Compaction Divider — shows token count when available */}
                    {t.isCompaction && (
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
                    <div className={`flex flex-col ${t.isUser ? 'items-end' : 'items-start'} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
                        <div className="flex items-center gap-2 mb-1.5 opacity-60">
                            <span className="text-[9px] glass-label text-text-secondary tracking-widest">{t.isUser ? 'USER' : 'ALLUCI'}</span>
                            <span className="text-[8px] font-mono text-text-tertiary">[{getFormattedTime(t.timestamp)}]</span>
                        </div>
                        <div className={`relative group max-w-[85%] md:max-w-[70%] px-5 py-3.5 text-[14px] leading-relaxed shadow-lg backdrop-blur-xl ${t.isUser ? 'bg-[rgba(0,113,227,0.18)] border border-[rgba(0,113,227,0.30)] text-text-primary rounded-[20px] rounded-br-[4px]' : 'bg-glass-2 border border-glass-edge text-text-primary rounded-[20px] rounded-bl-[4px]'}`}>
                            {t.text}
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
                </div>
            ))}
            {isProcessing && <ReadingIndicator />}
            <div ref={messagesEndRef} className="h-4 flex-none" />

            {/* Jump-to-bottom FAB — appears when scrolled up */}
            <JumpToNewButton
                scrollContainerRef={scrollContainerRef}
                messagesEndRef={messagesEndRef}
            />
            </div>
        </div>
    );
};

export default TerminalView;
