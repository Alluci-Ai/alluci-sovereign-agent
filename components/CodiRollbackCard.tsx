import React, { useState } from 'react';
import { RotateCcw, CheckCircle2, ShieldAlert, FileCode2, Clock } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

export interface CheckpointManifest {
    checkpoint_id: string;
    task_id: string;
    description: string;
    timestamp: number;
    created_at: string;
    status: 'active' | 'rolled_back';
    files: Record<string, { existed: boolean; sha256: string | null; size_bytes: number }>;
}

interface CodiRollbackCardProps {
    checkpoint: CheckpointManifest;
    onRollbackComplete?: (checkpointId: string) => void;
}

export const CodiRollbackCard: React.FC<CodiRollbackCardProps> = ({
    checkpoint,
    onRollbackComplete
}) => {
    const [isRollingBack, setIsRollingBack] = useState(false);
    const [status, setStatus] = useState<'active' | 'rolled_back'>(checkpoint.status);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);

    const fileEntries = Object.entries(checkpoint.files || {});

    const handleRollback = async () => {
        if (status === 'rolled_back') return;
        setIsRollingBack(true);
        setErrorMsg(null);

        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/checkpoints/${checkpoint.checkpoint_id}/rollback`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({ detail: 'Rollback failed' }));
                throw new Error(errData.detail || 'Rollback failed');
            }

            setStatus('rolled_back');
            if (onRollbackComplete) {
                onRollbackComplete(checkpoint.checkpoint_id);
            }
        } catch (err: any) {
            setErrorMsg(err.message || 'Rollback execution failed');
        } finally {
            setIsRollingBack(false);
        }
    };

    return (
        <div style={{
            background: 'var(--bg-elevated)',
            border: `1px solid ${status === 'rolled_back' ? 'var(--separator)' : 'rgba(10, 132, 255, 0.3)'}`,
            borderRadius: 12,
            padding: 16,
            marginBottom: 12,
            boxShadow: 'var(--glass-shadow-sm)',
            transition: 'all 0.2s ease'
        }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <FileCode2 size={16} color="var(--accent-blue)" />
                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                        {checkpoint.description || 'Codi Refactoring Task'}
                    </span>
                </div>
                <div style={{
                    fontSize: 11,
                    fontWeight: 600,
                    padding: '2px 8px',
                    borderRadius: 12,
                    background: status === 'rolled_back' ? 'var(--fill-quaternary)' : 'rgba(48, 209, 88, 0.15)',
                    color: status === 'rolled_back' ? 'var(--text-tertiary)' : 'var(--accent-green)',
                    border: `1px solid ${status === 'rolled_back' ? 'transparent' : 'rgba(48, 209, 88, 0.3)'}`
                }}>
                    {status === 'rolled_back' ? 'ROLLED BACK' : 'ACTIVE CHECKPOINT'}
                </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 12, fontSize: 11, color: 'var(--text-tertiary)', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Clock size={12} />
                    <span>{new Date(checkpoint.timestamp * 1000).toLocaleTimeString()}</span>
                </div>
                <span>ID: <code>{checkpoint.checkpoint_id}</code></span>
                <span>•</span>
                <span>{fileEntries.length} {fileEntries.length === 1 ? 'file' : 'files'} anchored</span>
            </div>

            {/* Target Files List */}
            <div style={{
                background: 'var(--bg-card)',
                borderRadius: 8,
                padding: '8px 10px',
                marginBottom: 12,
                maxHeight: 110,
                overflowY: 'auto'
            }}>
                {fileEntries.map(([path, meta]) => (
                    <div key={path} style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        fontSize: 11,
                        fontFamily: 'monospace',
                        color: 'var(--text-secondary)',
                        padding: '3px 0'
                    }}>
                        <span style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', maxWidth: '75%' }}>
                            {path}
                        </span>
                        <span style={{ fontSize: 10, color: meta.existed ? 'var(--text-tertiary)' : 'var(--accent-blue)' }}>
                            {meta.existed ? `${(meta.size_bytes / 1024).toFixed(1)} KB` : '[NEW FILE]'}
                        </span>
                    </div>
                ))}
            </div>

            {errorMsg && (
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    color: 'var(--accent-danger)',
                    fontSize: 11,
                    marginBottom: 10
                }}>
                    <ShieldAlert size={13} />
                    <span>{errorMsg}</span>
                </div>
            )}

            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                {status === 'active' ? (
                    <button
                        onClick={handleRollback}
                        disabled={isRollingBack}
                        className="glass-btn"
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 6,
                            padding: '6px 12px',
                            fontSize: 12,
                            fontWeight: 500,
                            color: 'var(--accent-danger)',
                            borderColor: 'rgba(255, 69, 58, 0.3)',
                            background: 'rgba(255, 69, 58, 0.08)',
                            cursor: isRollingBack ? 'not-allowed' : 'pointer'
                        }}
                    >
                        <RotateCcw size={13} className={isRollingBack ? 'animate-spin' : ''} />
                        <span>{isRollingBack ? 'Restoring Pre-State...' : 'Rollback Changes (1-Click)'}</span>
                    </button>
                ) : (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--text-tertiary)', fontSize: 11 }}>
                        <CheckCircle2 size={13} color="var(--accent-green)" />
                        <span>Working tree successfully reverted to pre-mutation state</span>
                    </div>
                )}
            </div>
        </div>
    );
};

export default CodiRollbackCard;
