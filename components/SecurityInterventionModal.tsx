import React, { useState } from 'react';
import { useStore } from '../store/useStore';
import { adminService } from '../adminService';
import './SecurityInterventionModal.css';

export const SecurityInterventionModal: React.FC = () => {
    const { pendingSecurityResolution, setPendingSecurityResolution } = useStore();
    const [loading, setLoading] = useState(false);

    if (!pendingSecurityResolution) return null;

    const handleAction = async (resolutionType: string) => {
        setLoading(true);
        try {
            // Note: In a real app we might use a dedicated securityService
            // Here we use fetch directly to our new endpoint
            const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';
            const response = await fetch(`${DAEMON_URL}/api/v1/security/resolve`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${useStore.getState().accessToken}`
                },
                body: JSON.stringify({
                    task_id: pendingSecurityResolution.task_id,
                    resolution_type: resolutionType,
                    metadata: pendingSecurityResolution.metadata
                })
            });

            if (!response.ok) {
                console.error("Failed to resolve security block:", await response.text());
                // In a production scenario, we'd show a toast error here
            }

            // Optimistic close
            setPendingSecurityResolution(null);
        } catch (e) {
            console.error("Error sending security resolution", e);
        } finally {
            setLoading(false);
        }
    };

    let title = "Security Block";
    let icon = "🛑";

    if (pendingSecurityResolution.exception_type === "DOMAIN_BLOCK") {
        title = "Untrusted Domain Blocked";
        icon = "🌐";
    } else if (pendingSecurityResolution.exception_type === "BUDGET_EXCEEDED") {
        title = "Financial Circuit Breaker";
        icon = "💳";
    } else if (pendingSecurityResolution.exception_type === "MANIFOLD_TEARING") {
        title = "Manifold Tearing Detected";
        icon = "⚠️";
    }

    return (
        <div className="security-intervention-overlay">
            <div className="security-intervention-modal">
                <div className="security-intervention-header">
                    <div className="security-intervention-icon-box">
                        <span className="security-intervention-icon">{icon}</span>
                    </div>
                    <div className="security-intervention-header-text">
                        <h2>{title}</h2>
                        <p>The agent requires your authorization to proceed.</p>
                    </div>
                </div>

                <div className="security-intervention-body">
                    <div className="security-intervention-message-card">
                        <p>{pendingSecurityResolution.message}</p>
                    </div>

                    <div className="security-intervention-actions">
                        {pendingSecurityResolution.exception_type === "DOMAIN_BLOCK" && (
                            <>
                                <button
                                    className="security-btn btn-primary"
                                    onClick={() => handleAction("ALLOW_DOMAIN_SESSION")}
                                    disabled={loading}
                                >
                                    Allow Once (Trust for this session)
                                </button>
                                <button
                                    className="security-btn btn-secondary"
                                    onClick={() => handleAction("ALLOW_DOMAIN_PERMANENT")}
                                    disabled={loading}
                                >
                                    Always Allow (Permanently trust)
                                </button>
                            </>
                        )}
                        
                        {pendingSecurityResolution.exception_type === "BUDGET_EXCEEDED" && (
                            <button
                                className="security-btn btn-primary"
                                onClick={() => handleAction("IGNORE_BUDGET")}
                                disabled={loading}
                            >
                                Temporarily Increase Budget & Resume
                            </button>
                        )}

                        {pendingSecurityResolution.exception_type === "MANIFOLD_TEARING" && (
                            <button
                                className="security-btn btn-primary"
                                onClick={() => handleAction("OVERRIDE_TEARING")}
                                disabled={loading}
                            >
                                Authorize Topology Shift (Discovery Mode)
                            </button>
                        )}

                        <button
                            className="security-btn btn-danger"
                            onClick={() => handleAction("CANCEL_TASK")}
                            disabled={loading}
                        >
                            Cancel Task
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
