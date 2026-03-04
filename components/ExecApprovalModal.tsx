import React, { useState } from 'react';
import { useStore } from '../store/useStore';
import { adminService } from '../adminService';
import './ExecApprovalModal.css';

export const ExecApprovalModal: React.FC = () => {
    const { pendingApproval, setPendingApproval } = useStore();
    const [loading, setLoading] = useState(false);

    if (!pendingApproval) return null;

    const handleAction = (approved: boolean, persist: boolean = false) => {
        setLoading(true);
        try {
            const method = approved ? 'exec.allow' : 'exec.deny';
            adminService.sendRPC(method, {
                request_id: pendingApproval.request_id,
                persist,
                command: pendingApproval.command,
                tool_name: pendingApproval.tool_name
            });

            // Optimistic close
            setPendingApproval(null);
        } catch (e) {
            console.error("Error sending approval RPC", e);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="exec-approval-overlay">
            <div className="exec-approval-modal">
                <div className="exec-approval-content">
                    <div className="exec-approval-header">
                        <div className="exec-approval-icon-box">
                            <span className="exec-approval-icon">🛡️</span>
                        </div>
                        <div className="exec-approval-header-text">
                            <h2 className="exec-approval-title">Sovereign Intercept</h2>
                            <p className="exec-approval-subtitle">Sensitive execution requires verification</p>
                        </div>
                    </div>

                    <div className="exec-approval-info-card">
                        <div className="exec-approval-info-label">
                            <span className="exec-approval-info-tag">Tool</span>
                            <span className="exec-approval-info-tool">{pendingApproval.tool_name}</span>
                        </div>
                        <pre className="exec-approval-command-pre">
                            {pendingApproval.command}
                        </pre>
                    </div>

                    <div className="exec-approval-body">
                        <p style={{ fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 16, textAlign: 'center' }}>
                            Decision will be logged to the Simplicial Audit Trail.
                        </p>

                        <div className="exec-approval-actions-triad">
                            <button
                                onClick={() => handleAction(false, true)}
                                disabled={loading}
                                className="exec-approval-btn deny-always"
                            >
                                Block Always
                            </button>
                            <button
                                onClick={() => handleAction(false, false)}
                                disabled={loading}
                                className="exec-approval-btn deny-once"
                            >
                                Deny
                            </button>
                            <div style={{ width: 1, background: 'var(--separator)', height: 28 }} />
                            <button
                                onClick={() => handleAction(true, false)}
                                disabled={loading}
                                className="exec-approval-btn allow-once"
                            >
                                Allow Once
                            </button>
                            <button
                                onClick={() => handleAction(true, true)}
                                disabled={loading}
                                className="exec-approval-btn allow-always"
                            >
                                Allow Always
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
