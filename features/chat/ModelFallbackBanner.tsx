import React, { useEffect } from 'react';
import { useStore } from '../../store/useStore';
import { AlertTriangle } from 'lucide-react';

/**
 * ModelFallbackBanner — Notification when the model router
 * falls back to an alternative model. Auto-dismisses after 10s.
 */
export const ModelFallbackBanner: React.FC = () => {
    const { modelFallbackMessage, setModelFallbackMessage } = useStore();

    useEffect(() => {
        if (modelFallbackMessage) {
            const timer = setTimeout(() => setModelFallbackMessage(null), 10000);
            return () => clearTimeout(timer);
        }
    }, [modelFallbackMessage]);

    if (!modelFallbackMessage) return null;

    return (
        <div className="model-fallback-banner">
            <AlertTriangle size={14} />
            <span>{modelFallbackMessage}</span>
            <button
                onClick={() => setModelFallbackMessage(null)}
                className="model-fallback-banner__dismiss"
            >
                ✕
            </button>
        </div>
    );
};

export default ModelFallbackBanner;
