
import React, { useState } from 'react';
import { X, RotateCcw, ChevronDown, ChevronRight } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import type { TaskRecord } from '../types';
import { formatDuration } from '../utils/time';
import { useStore } from '../../../store/useStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://127.0.0.1:8000';

interface Props {
  task: TaskRecord;
  runId: number;
  onClose: () => void;
  onRetry: () => void;
}

const JsonBlock: React.FC<{ value: any; label: string }> = ({ value, label }) => {
  const [open, setOpen] = useState(true);
  const str = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  return (
    <div style={{ marginBottom: 12 }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', gap: 4, background: 'none', border: 'none',
          cursor: 'pointer', padding: 0, marginBottom: 6,
          color: 'var(--text-tertiary)', fontSize: 10, fontFamily: 'var(--font-mono)',
          textTransform: 'uppercase', letterSpacing: '0.08em',
        }}
      >
        {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />} {label}
      </button>
      {open && (
        <pre style={{
          margin: 0, padding: '10px 12px', borderRadius: 8,
          background: 'rgba(0,0,0,0.20)', border: '1px solid var(--separator)',
          fontFamily: 'var(--font-mono)', fontSize: 10, lineHeight: 1.6,
          color: 'var(--accent-warm)', overflowX: 'auto', whiteSpace: 'pre-wrap',
          wordBreak: 'break-all', maxHeight: 200,
        }}>
          {str || '—'}
        </pre>
      )}
    </div>
  );
};

export const TaskDetailDrawer: React.FC<Props> = ({ task, runId, onClose, onRetry }) => {
  const { accessToken } = useStore();
  const [retrying, setRetrying] = useState(false);

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await fetch(`${DAEMON_URL}/api/v1/dag/runs/${runId}/tasks/${task.task_dag_id}/retry`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` },
        credentials: 'include',
      });
      onRetry();
    } finally {
      setRetrying(false);
    }
  };

  return (
    <div data-testid="task-detail-drawer" className="dag-task-drawer" style={{
      position: 'absolute', top: 0, right: 0, bottom: 0,
      width: 360, zIndex: 50,
      background: 'var(--glass-bg)',
      backdropFilter: 'var(--glass-blur-heavy) var(--glass-sat)',
      WebkitBackdropFilter: 'var(--glass-blur-heavy) var(--glass-sat)',
      borderLeft: '1px solid var(--glass-edge)',
      boxShadow: 'var(--glass-shadow-lg)',
      display: 'flex', flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{
        padding: '14px 16px', borderBottom: '1px solid var(--separator)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
            <StatusBadge status={task.status} />
            <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>
              {task.task_dag_id}
            </span>
          </div>
          <h4 style={{
            margin: 0, fontSize: 13, fontWeight: 600,
            fontFamily: 'var(--font-mono)', color: 'var(--text-primary)',
            textTransform: 'uppercase', letterSpacing: '0.04em',
          }}>
            {task.action}
          </h4>
        </div>
        <button onClick={onClose} className="glass-btn" style={{ padding: '4px 6px' }}>
          <X size={13} />
        </button>
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 16px' }} className="scrollbar-hide">
        <div style={{
          display: 'flex', gap: 12, padding: '10px 12px', borderRadius: 8,
          background: 'var(--fill-quaternary)', border: '1px solid var(--separator)',
          marginBottom: 16,
        }}>
          {[
            { label: 'STARTED', value: task.start_time ? new Date(task.start_time).toLocaleTimeString() : '—' },
            { label: 'DURATION', value: task.start_time ? formatDuration(task.start_time, task.end_time) : '—' },
            { label: 'RETRIES', value: task.retry_count ?? 0 },
          ].map(({ label, value }) => (
            <div key={label} style={{ flex: 1, textAlign: 'center' }}>
              <div style={{ fontSize: 9, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em' }}>{label}</div>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{String(value)}</div>
            </div>
          ))}
        </div>

        <JsonBlock value={task.args} label="Input Args" />
        {task.result && <JsonBlock value={task.result} label="Output" />}

        {task.error && (
          <div style={{ marginBottom: 12 }}>
            <p className="glass-label" style={{ fontSize: 9, color: 'var(--accent-danger)', marginBottom: 6 }}>ERROR</p>
            <pre style={{
              margin: 0, padding: '10px 12px', borderRadius: 8,
              background: 'var(--liquid-danger)', border: '1px solid var(--liquid-danger-edge)',
              fontFamily: 'var(--font-mono)', fontSize: 10, lineHeight: 1.6,
              color: 'var(--accent-danger)', overflowX: 'auto', whiteSpace: 'pre-wrap',
            }}>
              {task.error}
            </pre>
          </div>
        )}
      </div>

      {task.status === 'failed' && (
        <div style={{ padding: '12px 16px', borderTop: '1px solid var(--separator)' }}>
          <button
            onClick={handleRetry}
            disabled={retrying}
            className="glass-btn glass-btn--primary"
            style={{
              width: '100%', padding: '9px', fontSize: 12,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            }}
          >
            <RotateCcw size={12} className={retrying ? 'animate-spin' : ''} />
            {retrying ? 'Retrying...' : 'Retry Task'}
          </button>
        </div>
      )}

      {task.action === 'spawn_sub_agent' && task.args?.agent_id && (
        <div style={{ padding: '12px 16px', borderTop: '1px solid var(--separator)' }}>
          <button
            onClick={() => {
              useStore.getState().setActiveAgentId(task.args.agent_id);
              onClose();
            }}
            className="glass-btn glass-btn--primary"
            style={{
              width: '100%', padding: '9px', fontSize: 12,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            }}
          >
            <ChevronRight size={12} />
            Switch Context to Sub-Agent
          </button>
        </div>
      )}
    </div>
  );
};
