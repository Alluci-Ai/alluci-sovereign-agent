import React from 'react';
import { useVoiceStream } from '../../hooks/useVoiceStream';
import { useStore } from '../../store/useStore';
import { AutonomyLevel } from '../../kernel/types';
import { AudioWaveformVisualizer } from '../../components/AudioWaveformVisualizer';

interface CommandBarProps {
    textInput: string;
    setTextInput: (val: string) => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    attachments: any[];
    removeAttachment: (idx: number) => void;
    fileInputRef: React.RefObject<HTMLInputElement | null>;
    handleFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
    handleCommandSubmit: (e: React.FormEvent) => void;
    handlePaste: (e: React.ClipboardEvent) => void;
    isProcessing: boolean;
    bridgeManagerRef: React.RefObject<any>;
}

const CommandBar: React.FC<CommandBarProps> = ({
    textInput,
    setTextInput,
    attachments,
    removeAttachment,
    fileInputRef,
    handleFileChange,
    handleCommandSubmit,
    handlePaste,
    isProcessing,
    bridgeManagerRef
}) => {
    const { setTranscriptions } = useStore();
    
    const { isRecording, isAgentSpeaking, isConnected, toggleRecording, stream } = useVoiceStream(
        (text, isFinal) => {
            setTextInput(text);
        },
        (finalText) => {
            // Auto submit when utterance is finalized
            onSubmit(new Event('submit') as any);
        }
    );
    
    const theme = useStore(state => state.theme);
    const [inputMode, setInputMode] = React.useState<'chat' | 'dispatch'>('chat');

    const handleStopAndSubmit = async () => {
        toggleRecording();
        const currentText = textInput.trim();
        if (currentText) {
            onSubmit(new Event('submit') as any);
        }
    };

    const onSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (isProcessing) return;
        if (inputMode === 'chat') {
            handleCommandSubmit(e);
        } else {
            const currentText = textInput.trim();
            if (!currentText) return;
            setTextInput("");
            useStore.getState().setTranscriptions(prev => [...prev, { text: currentText, isUser: true, timestamp: new Date().toISOString(), type: 'dispatch' }]);
            const token = useStore.getState().accessToken;
            useStore.getState().setIsProcessing(true);
            try {
                // Determine current biometrics for ACE evaluation
                const state = useStore.getState();
                const token = state.accessToken || '';
                
                const aceState = {
                    physicalEnergy: state.biometrics?.physical || 0.5,
                    emotionalValence: state.biometrics?.emotional || 0.5,
                    cognitiveLoad: state.biometrics?.cognitive || 0.5,
                };
                
                const { submitObjective } = await import('../../lib/objectiveService');
                const res = await submitObjective(
                     currentText,
                     AutonomyLevel.SOVEREIGN,
                     [], // vaultScope
                     [], // capabilityScope
                     aceState,
                     token
                );
                
                if (res.status === 'halted' || res.status === 'failed') {
                    throw new Error(res.reason || `Objective ${res.status}`);
                }
                
                useStore.getState().setTranscriptions(prev => [...prev, { text: "Objective dispatched successfully. Tracking in DAG Manifold.", isUser: false, timestamp: new Date().toISOString(), type: 'dispatch' }]);
            } catch (err: any) {
                 useStore.getState().setTranscriptions(prev => [...prev, { text: `[ ERROR ]: ${err.message || 'Failed to dispatch objective.'}`, isUser: false, timestamp: new Date().toISOString(), type: 'dispatch' }]);
            } finally {
                 useStore.getState().setIsProcessing(false);
            }
        }
    };

    return (
        <form onSubmit={onSubmit} className="shrink-0 p-4 md:p-6 flex flex-col gap-2 z-10 w-full max-w-4xl mx-auto mb-4">
            {/* Input Mode Toggle */}
            <div className="flex px-2 mb-1">
                <div className="bg-glass-2 rounded-full p-1 flex gap-1 shadow-inner border border-glass-edge backdrop-blur-md">
                    <button 
                        type="button" 
                        onClick={() => setInputMode('chat')}
                        className={`px-4 py-1.5 text-[11px] font-bold rounded-full transition-all ${inputMode === 'chat' ? (theme === 'light' ? 'bg-[rgba(0,0,0,0.06)] text-black shadow-sm' : 'bg-[rgba(255,255,255,0.15)] text-white shadow-sm') : 'text-text-tertiary hover:text-text-secondary'}`}
                    >
                        Conversational
                    </button>
                    <button 
                        type="button" 
                        onClick={() => setInputMode('dispatch')}
                        className={`px-4 py-1.5 text-[11px] font-bold rounded-full transition-all ${inputMode === 'dispatch' ? 'bg-[rgba(255,159,10,0.2)] text-accent-warm shadow-sm border border-[rgba(255,159,10,0.3)]' : 'text-text-tertiary hover:text-text-secondary'}`}
                    >
                        Objective Dispatch
                    </button>
                </div>
            </div>
            {attachments.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-2 px-2">
                    {attachments.map((file, idx) => (
                        <div key={idx} className="flex items-center gap-2 bg-glass-2 border border-glass-edge rounded-full px-4 py-1.5 text-[10px] glass-label animate-in slide-in-from-bottom-2 shadow-sm text-text-primary">
                            <span className="opacity-50">{file.mimeType.split('/')[0].toUpperCase()}</span>
                            <span className="truncate max-w-[150px] font-bold">{file.name}</span>
                            <button type="button" onClick={() => removeAttachment(idx)} className="text-tension hover:text-white transition-colors px-1 font-bold ml-1 hover:bg-tension/20 rounded-full w-5 h-5 flex items-center justify-center">✕</button>
                        </div>
                    ))}
                </div>
            )}
            <div className="flex gap-2 items-center bg-glass-1 backdrop-blur-xl border border-glass-edge rounded-full p-1.5 shadow-lg">
                <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    title="Ingest Data"
                    className="shrink-0 flex items-center justify-center"
                    style={{
                        width: 40,
                        height: 40,
                        borderRadius: '50%',
                        border: '1px solid var(--separator)',
                        background: 'var(--fill-quaternary)',
                        color: 'var(--text-secondary)',
                        fontSize: 20,
                        fontWeight: 300,
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                        lineHeight: 1,
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--fill-tertiary)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--fill-quaternary)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
                >
                    +
                </button>
                <input type="file" ref={fileInputRef} onChange={handleFileChange} multiple className="hidden" />

                <button
                    type="button"
                    onClick={isRecording ? handleStopAndSubmit : toggleRecording}
                    title={isRecording ? "Stop Recording" : "Click to Speak"}
                    className={`shrink-0 flex items-center justify-center transition-all duration-200 ml-1 ${isRecording ? 'scale-110 shadow-[0_0_15px_rgba(255,125,0,0.4)] animate-pulse' : ''}`}
                    style={{
                        width: 40,
                        height: 40,
                        borderRadius: '50%',
                        border: isRecording ? '1.5px solid var(--tension)' : '1px solid var(--separator)',
                        background: isRecording ? 'rgba(255,125,0,0.1)' : 'var(--fill-quaternary)',
                        color: isRecording ? 'var(--tension)' : 'var(--text-secondary)',
                        cursor: 'pointer',
                    }}
                >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                        <line x1="12" y1="19" x2="12" y2="23" />
                        <line x1="8" y1="23" x2="16" y2="23" />
                    </svg>
                </button>

                {isRecording && (
                    <div className="flex-1 max-w-xs md:max-w-md mx-2">
                        <AudioWaveformVisualizer stream={stream} analyser={null} />
                    </div>
                )}

                <textarea
                    value={textInput}
                    onChange={(e) => setTextInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); onSubmit(e); } }}
                    onPaste={handlePaste}
                    placeholder={isProcessing ? "Adding to replay queue..." : (isRecording ? "Listening..." : "Ask Alluci...")}
                    className="flex-1 bg-transparent border-none text-[14px] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-0 p-3 h-10 md:h-12 resize-none scrollbar-hide py-3 md:py-3.5"
                    rows={1}
                />

                <button
                    type="submit"
                    className="shrink-0 flex items-center justify-center mr-1"
                    style={{
                        width: 40,
                        height: 40,
                        borderRadius: '50%',
                        border: '0.5px solid var(--liquid-accent-edge)',
                        background: 'var(--liquid-accent)',
                        backdropFilter: 'blur(20px) saturate(180%)',
                        WebkitBackdropFilter: 'blur(20px) saturate(180%)',
                        color: 'var(--accent)',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                        boxShadow: 'var(--liquid-inner-glow), 0 1px 6px rgba(48, 209, 88, 0.12)',
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--liquid-accent-hover)'; e.currentTarget.style.transform = 'translateY(-1px)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--liquid-accent)'; e.currentTarget.style.transform = 'translateY(0)'; }}
                >
                    {isProcessing ? (
                        <div className="flex items-center justify-center w-full h-full relative">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" style={{ animation: 'spin 2s linear infinite' }} className="absolute opacity-40">
                                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2.5" strokeDasharray="31.4 31.4" strokeLinecap="round" />
                            </svg>
                            <span className="text-[10px] font-bold">+</span>
                        </div>
                    ) : (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="12" y1="19" x2="12" y2="5" />
                            <polyline points="5 12 12 5 19 12" />
                        </svg>
                    )}
                </button>
            </div>
        </form>
    );
};

export default CommandBar;
