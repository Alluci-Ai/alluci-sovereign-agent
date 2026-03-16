import React, { useRef, useCallback } from 'react';
import { useStore } from '../../store/useStore';
import { Square } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

/**
 * AbortButton — Floating "Stop Generation" control.
 *
 * Production behavior:
 *  1. Fires AbortController.abort() on the shared controller ref to cancel
 *     any in-flight fetch (backend proxy) or Gemini SDK call client-side.
 *  2. Sends POST /api/v1/chat/abort to cancel any server-side streaming.
 *  3. Clears the isProcessing flag and appends an ABORTED message.
 *
 * Visual: red translucent pill with ■ icon, fades in via CSS keyframe
 *         during isProcessing, fades out when isProcessing becomes false.
 */
interface AbortButtonProps {
    /** Shared AbortController ref — created per-request in useInteractions */
    abortControllerRef: React.RefObject<AbortController | null>;
    /** Callback to finalize abort (clear state, append message) */
    onAbort: () => void;
}

export const AbortButton: React.FC<AbortButtonProps> = ({ abortControllerRef, onAbort }) => {
    const { isProcessing, accessToken } = useStore();
    const isAborting = useRef(false);

    const handleAbort = useCallback(async () => {
        if (isAborting.current) return; // Prevent double-fire
        isAborting.current = true;

        // 1. Client-side: signal the AbortController
        try {
            abortControllerRef.current?.abort();
        } catch { /* Already aborted or null — safe to ignore */ }

        // 2. Server-side: POST /api/v1/chat/abort to cancel streaming backend
        try {
            await fetch(`${DAEMON_URL}/api/v1/chat/abort`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
                },
                credentials: 'include',
                // Short timeout — best-effort, don't block the UI
                signal: AbortSignal.timeout(3000),
            });
        } catch {
            // Server unreachable or abort already completed — acceptable
        }

        // 3. Fire the parent callback to clear processing state
        onAbort();
        isAborting.current = false;
    }, [abortControllerRef, onAbort, accessToken]);

    if (!isProcessing) return null;

    return (
        <button
            onClick={handleAbort}
            className="abort-button"
            title="Stop generation (Esc)"
            aria-label="Stop generation"
        >
            <Square size={11} fill="currentColor" />
            <span className="abort-button__label">Stop</span>
        </button>
    );
};

export default AbortButton;
