
import React from 'react';
import { RefreshCw, StopCircle } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import type { DAGRun, TaskRecord, StreamStatus } from '../types';
import { formatDuration } from '../utils/time';

interface Props {
  run: DAGRun;
  tasks: TaskRecord[];
  streamStatus: StreamStatus;
  onCancel: () => void;
  onRefresh: () => void;
}

export const RunDetailHeader: React.FC<Props> = ({ run, tasks, streamStatus, onCancel, onRefresh }) => {
  const completed = tasks.filter(t => t.status === 'completed').length;
  const total = tasks.length;
  const progress = total > 0 ? (completed / total) * 100 : 0;
  const isActive = run.status === 'active';

  return (
    <div data-testid="run-detail-header" style={{
      padding: '14px 18px', borderBottom: '1px solid var(--separator)',
      background: 'var(--glass-bg)',
      backdropFilter: 'var(--glass-blur)',
      WebkitBackdropFilter: 'var(--glass-blur)',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 10 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <StatusBadge status={run.status} />
            <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>
              RUN_{run.id}
            </span>
            {streamStatus === 'live' && (
              <span style={{ fontSize: 9, color: 'var(--accent-warm)', fontFamily: 'var(--font-mono)', letterSpacing: '0.06em' }}>
                ● LIVE
              </span>
            )}
          </div>
          <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', margin: 0, lineHeight: 1.4 }}>
            {run.objective}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
          <button onClick={onRefresh} className="glass-btn" style={{ padding: '5px 8px', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
            <RefreshCw size={11} />
          </button>
          {isActive && (
            <button onClick={onCancel} className="glass-btn" style={{
              padding: '5px 10px', display: 'flex', alignItems: 'center', gap: 5, fontSize: 11,
              color: 'var(--accent-danger)', borderColor: 'var(--liquid-danger-edge)',
              background: 'var(--liquid-danger)',
            }}>
              <StopCircle size={11} /> Cancel
            </button>
          )}
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ flex: 1, height: 4, borderRadius: 2, background: 'var(--fill-quaternary)', overflow: 'hidden' }}>
          <div className="dag-progress-fill" style={{
            height: '100%', borderRadius: 2,
            width: `${progress}%`,
            background: run.status === 'failed' ? 'var(--accent-danger)' : 'var(--accent)',
          }} />
        </div>
        <div style={{ display: 'flex', gap: 16, flexShrink: 0 }}>
          {[
            { label: 'TASKS', value: `${completed}/${total}` },
            { label: 'FAILED', value: tasks.filter(t => t.status === 'failed').length },
            { label: 'ELAPSED', value: run.started_at ? formatDuration(run.started_at, run.completed_at) : '—' },
          ].map(({ label, value }) => (
            <div key={label} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 9, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em' }}>
                {label}
              </div>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                {value}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
