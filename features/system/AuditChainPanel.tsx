import React from 'react';
import { useStore } from '../../store/useStore';

interface AuditChainPanelProps {
    refreshAuditLog: () => void;
}

const AuditChainPanel: React.FC<AuditChainPanelProps> = ({ refreshAuditLog }) => {
    const { auditLog } = useStore();

    return (
        <div className="inline-panel">
            <div className="inline-panel__header">
                <h2 className="inline-panel__title">Executive Ledger</h2>
                <button onClick={refreshAuditLog} className="glass-btn text-xs">
                    Refresh
                </button>
            </div>
            <div className="inline-panel__body">
                {auditLog.length === 0 ? (
                    <div className="inline-panel__empty">
                        <p>No audit entries recorded yet.</p>
                        <p className="text-xs opacity-50">Events will appear here as system operations occur.</p>
                    </div>
                ) : (
                    <div className="flex flex-col gap-3">
                        {auditLog.map((e, i) => (
                            <div key={i} className="audit-entry">
                                <div className="audit-entry__indicator" />
                                <span className="audit-entry__timestamp">{e.timestamp}</span>
                                <span className="audit-entry__event">{e.event}</span>
                                <span className="audit-entry__details">{JSON.stringify(e.details)}</span>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default AuditChainPanel;
