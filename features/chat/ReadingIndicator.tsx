import React from 'react';

/**
 * ReadingIndicator — Animated CSS indicator shown during the 
 * "thinking" / reasoning phase of the AI before the first token streams back.
 * 
 * Uses pure CSS keyframes (see styles/tokens.css) to bounce three dots.
 */
export const ReadingIndicator: React.FC = () => {
    return (
        <div className="flex flex-col items-start animate-in fade-in slide-in-from-bottom-2 duration-300">
            <div className="flex items-center gap-2 mb-1.5 opacity-60">
                <span className="text-[9px] glass-label text-text-secondary tracking-widest">ALLUCI</span>
                <span className="text-[8px] font-mono text-text-tertiary">[{new Date().toLocaleTimeString()}]</span>
            </div>
            <div className="relative max-w-[85%] md:max-w-[70%] px-5 py-3.5 shadow-lg backdrop-blur-xl bg-glass-2 border border-glass-edge rounded-[20px] rounded-bl-[4px] flex items-center gap-1 min-h-[44px]">
                <div className="w-1.5 h-1.5 bg-text-primary rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                <div className="w-1.5 h-1.5 bg-text-primary rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                <div className="w-1.5 h-1.5 bg-text-primary rounded-full animate-bounce"></div>
            </div>
        </div>
    );
};

export default ReadingIndicator;
