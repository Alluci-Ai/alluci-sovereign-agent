import React, { useEffect, useCallback } from 'react';
import { useStore } from '../../store/useStore';
import { Maximize2, Minimize2 } from 'lucide-react';

/**
 * FocusModeToggle — Collapses sidebar and hides the artifact pane
 * to maximize the chat area for distraction-free work.
 *
 * Production behavior:
 *  - Toggles focusMode in store, which CSS uses to animate the sidebar
 *    (width: 0, overflow: hidden, transition: width 0.3s)
 *  - Also collapses the sidebar via setSidebarCollapsed
 *  - Keyboard shortcut: Cmd/Ctrl + Shift + F
 *  - Renders in the chat topbar area (between title and right controls)
 */
export const FocusModeToggle: React.FC = () => {
    const { focusMode, setFocusMode, setSidebarCollapsed } = useStore();

    const toggle = useCallback(() => {
        const next = !focusMode;
        setFocusMode(next);
        setSidebarCollapsed(next);
    }, [focusMode, setFocusMode, setSidebarCollapsed]);

    // Keyboard shortcut: Cmd/Ctrl + Shift + F
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === 'F') {
                e.preventDefault();
                toggle();
            }
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [toggle]);

    return (
        <button
            onClick={toggle}
            className="focus-mode-toggle"
            title={focusMode ? 'Exit focus mode (⌘⇧F)' : 'Enter focus mode (⌘⇧F)'}
            aria-label={focusMode ? 'Exit focus mode' : 'Enter focus mode'}
            aria-pressed={focusMode}
        >
            {focusMode ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            <span className="focus-mode-toggle__label">
                {focusMode ? 'Exit Focus' : 'Focus'}
            </span>
        </button>
    );
};

export default FocusModeToggle;
