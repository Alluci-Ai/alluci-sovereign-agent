import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useStore } from '../../store/useStore';
import { ArrowDown } from 'lucide-react';

/**
 * JumpToNewButton — Sticky scroll-to-bottom FAB.
 *
 * Production behavior:
 *  - Appears when user scrolls ≥120px from bottom of transcript
 *  - Shows unread message count badge when new messages arrive while scrolled up
 *  - Smooth-scrolls to bottom on click, resets unseen counter
 *  - Auto-hides when user is already at the bottom
 *  - Throttled scroll listener (60fps RAF) to avoid layout thrashing
 */
interface JumpToNewButtonProps {
    scrollContainerRef: React.RefObject<HTMLDivElement | null>;
    messagesEndRef: React.RefObject<HTMLDivElement | null>;
}

export const JumpToNewButton: React.FC<JumpToNewButtonProps> = ({
    scrollContainerRef,
    messagesEndRef,
}) => {
    const { transcriptions } = useStore();
    const [isAtBottom, setIsAtBottom] = useState(true);
    const [unseenCount, setUnseenCount] = useState(0);
    const lastSeenLength = useRef(transcriptions.length);
    const rafId = useRef<number>(0);

    // Throttled scroll detection using requestAnimationFrame
    const handleScroll = useCallback(() => {
        cancelAnimationFrame(rafId.current);
        rafId.current = requestAnimationFrame(() => {
            const el = scrollContainerRef.current;
            if (!el) return;
            const threshold = 120;
            const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
            setIsAtBottom(atBottom);
            if (atBottom) {
                setUnseenCount(0);
                lastSeenLength.current = transcriptions.length;
            }
        });
    }, [scrollContainerRef, transcriptions.length]);

    // Track unseen count when new messages arrive while scrolled up
    useEffect(() => {
        if (!isAtBottom && transcriptions.length > lastSeenLength.current) {
            setUnseenCount(transcriptions.length - lastSeenLength.current);
        }
        if (isAtBottom) {
            lastSeenLength.current = transcriptions.length;
            setUnseenCount(0);
        }
    }, [transcriptions.length, isAtBottom]);

    // Attach passive scroll listener
    useEffect(() => {
        const el = scrollContainerRef.current;
        if (!el) return;
        el.addEventListener('scroll', handleScroll, { passive: true });
        return () => {
            el.removeEventListener('scroll', handleScroll);
            cancelAnimationFrame(rafId.current);
        };
    }, [handleScroll, scrollContainerRef]);

    const jumpToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        setUnseenCount(0);
        lastSeenLength.current = transcriptions.length;
    }, [messagesEndRef, transcriptions.length]);

    if (isAtBottom) return null;

    return (
        <button
            onClick={jumpToBottom}
            className="jump-to-new-button"
            title={unseenCount > 0 ? `${unseenCount} new message${unseenCount > 1 ? 's' : ''}` : 'Jump to bottom'}
            aria-label={`Jump to latest messages${unseenCount > 0 ? `, ${unseenCount} new` : ''}`}
        >
            <ArrowDown size={16} />
            {unseenCount > 0 && (
                <span className="jump-to-new-button__badge">
                    {unseenCount > 99 ? '99+' : unseenCount}
                </span>
            )}
        </button>
    );
};

export default JumpToNewButton;
