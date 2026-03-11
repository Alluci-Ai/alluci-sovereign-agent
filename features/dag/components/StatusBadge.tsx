
import React from 'react';

type TaskStatusType = 'pending' | 'running' | 'completed' | 'failed' | 'skipped' | 'active' | 'queued';

const STATUS_STYLES: Record<string, React.CSSProperties> = {
  completed: { color: 'var(--accent)',           background: 'var(--liquid-accent)',     borderColor: 'var(--liquid-accent-edge)' },
  running:   { color: 'var(--accent-warm)',       background: 'var(--liquid-warm)',       borderColor: 'var(--liquid-warm-edge)' },
  active:    { color: 'var(--accent-warm)',       background: 'var(--liquid-warm)',       borderColor: 'var(--liquid-warm-edge)' },
  pending:   { color: 'var(--accent-secondary)',  background: 'var(--liquid-secondary)',  borderColor: 'var(--liquid-secondary-edge)' },
  queued:    { color: 'var(--accent-secondary)',  background: 'var(--liquid-secondary)',  borderColor: 'var(--liquid-secondary-edge)' },
  failed:    { color: 'var(--accent-danger)',     background: 'var(--liquid-danger)',     borderColor: 'var(--liquid-danger-edge)' },
  skipped:   { color: 'var(--text-tertiary)',     background: 'var(--fill-quaternary)',   borderColor: 'var(--separator)' },
};

export const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const styles = STATUS_STYLES[status] ?? STATUS_STYLES.pending;
  return (
    <span style={{
      ...styles,
      fontSize: 9, fontWeight: 700, fontFamily: 'var(--font-mono)',
      textTransform: 'uppercase', letterSpacing: '0.08em',
      padding: '2px 6px', borderRadius: 4,
      border: '1px solid', display: 'inline-flex', alignItems: 'center', gap: 4,
    }}>
      {status === 'running' && (
        <span style={{
          width: 5, height: 5, borderRadius: '50%',
          background: 'var(--accent-warm)',
          animation: 'pulse-dot 1.2s ease-in-out infinite',
          display: 'inline-block',
        }} />
      )}
      {status.toUpperCase()}
    </span>
  );
};
