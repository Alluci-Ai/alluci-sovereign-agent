
import React from 'react';
import { RefreshCw } from 'lucide-react';
import type { DAGRun } from '../types';
import { StatusBadge } from './StatusBadge';
import { formatRelativeTime } from '../utils/time';

interface Props {
  runs: DAGRun[];
  loading: boolean;
  selectedRunId: number | null;
  statusFilter: string;
  onStatusFilterChange: (v: string) => void;
  onSelectRun: (id: number) => void;
  onRefresh: () => void;
}

export const RunListSidebar: React.FC<Props> = ({
  runs, loading, selectedRunId, statusFilter, onStatusFilterChange, onSelectRun, onRefresh
}) => (
  <div style={{
    width: 260, flexShrink: 0, display: 'flex', flexDirection: 'column',
    borderRight: '1px solid var(--separator)', background: 'var(--bg-base)', height: '100%',
  }}>
    {/* Header */}
    <div style={{
      padding: '16px 14px 12px', borderBottom: '1px solid var(--separator)',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    }}>
      <div>
        <h3 style={{ fontSize: 15, fontWeight: 600, margin: 0, color: 'var(--text-primary)' }}>DAG Planner</h3>
        <span className="glass-label" style={{ fontSize: 9, color: 'var(--text-tertiary)' }}>
          EXECUTION_MANIFOLD
        </span>
      </div>
      <button
        onClick={onRefresh}
        className="glass-btn"
        style={{ padding: '4px 6px', display: 'flex', alignItems: 'center', gap: 4 }}
        title="Refresh runs"
      >
        <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
      </button>
    </div>

    {/* Filter */}
    <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--separator)' }}>
      <div style={{ display: 'flex', gap: 2, background: 'var(--fill-quaternary)', borderRadius: 8, padding: 2, border: '1px solid var(--separator)' }}>
        {['', 'active', 'completed', 'failed'].map(s => (
          <button
            key={s || 'all'}
            onClick={() => onStatusFilterChange(s)}
            style={{
              flex: 1, padding: '3px 4px', borderRadius: 6, fontSize: 9, fontWeight: 600,
              fontFamily: 'var(--font-mono)', textTransform: 'uppercase', border: 'none',
              cursor: 'pointer', letterSpacing: '0.05em',
              background: statusFilter === s ? 'var(--glass-bg-hover)' : 'transparent',
              color: statusFilter === s ? 'var(--text-primary)' : 'var(--text-tertiary)',
              boxShadow: statusFilter === s ? 'var(--glass-shadow)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            {s || 'ALL'}
          </button>
        ))}
      </div>
    </div>

    {/* Run List */}
    <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }} className="scrollbar-hide">
      {runs.length === 0 && !loading && (
        <div style={{ textAlign: 'center', padding: '40px 12px', color: 'var(--text-tertiary)' }}>
          <p style={{ fontSize: 10, fontFamily: 'var(--font-mono)', letterSpacing: '0.1em' }}>
            NO_RUNS_FOUND
          </p>
        </div>
      )}
      {runs.map(run => {
        const isSelected = run.id === selectedRunId;
        const isActive = run.status === 'active';
        return (
          <div
            key={run.id}
            onClick={() => onSelectRun(run.id)}
            className="dag-run-card"
            style={{
              padding: '10px 12px', borderRadius: 10, marginBottom: 4, cursor: 'pointer',
              background: isSelected ? 'var(--liquid-accent)' : 'var(--glass-bg)',
              border: `1px solid ${isSelected ? 'var(--liquid-accent-edge)' : 'var(--glass-edge)'}`,
              transition: 'all 0.15s ease',
            }}
          >
            <p style={{
              fontSize: 11, fontWeight: 500, color: 'var(--text-primary)',
              margin: '0 0 6px', lineHeight: 1.4,
              overflow: 'hidden', display: '-webkit-box',
              WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
            }}>
              {run.objective || '—'}
            </p>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 4 }}>
              <StatusBadge status={run.status} />
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                {run.tasks && run.tasks.length > 0 ? (
                  <span style={{ fontSize: 9, fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>
                    {run.tasks.filter(t => t.status === 'completed').length}/{run.tasks.length} ({Math.round((run.tasks.filter(t => t.status === 'completed').length / run.tasks.length) * 100)}%)
                  </span>
                ) : run.task_counts ? (
                  <span style={{ fontSize: 9, fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>
                    {run.task_counts.completed}/{run.task_counts.total}
                  </span>
                ) : null}
                <span style={{ fontSize: 9, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                  {formatRelativeTime(run.created_at || run.started_at || '')}
                </span>
              </div>
            </div>
            {run.tasks && run.tasks.length > 0 ? (
              <div style={{ marginTop: 6, width: '100%', height: 3, background: 'rgba(255,255,255,0.08)', borderRadius: 2, overflow: 'hidden' }}>
                <div style={{
                  height: '100%',
                  width: `${Math.round((run.tasks.filter(t => t.status === 'completed').length / run.tasks.length) * 100)}%`,
                  background: run.status === 'completed' ? 'var(--status-good)' : 'var(--accent-warm)',
                  transition: 'width 0.3s ease'
                }} />
              </div>
            ) : isActive ? (
              <div style={{
                marginTop: 6, height: 2, borderRadius: 2,
                background: 'var(--accent-warm)',
                animation: 'pulse-width 2s ease-in-out infinite',
              }} />
            ) : null}
          </div>
        );
      })}
    </div>
  </div>
);
