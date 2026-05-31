
import React, { useEffect, useState } from 'react';
import { X, Play, Loader, GitFork } from 'lucide-react';
import { useStore } from '../../../store/useStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://127.0.0.1:8000';

interface PreviewTask {
  id: string;
  action: string;
  description: string;
  dependencies: string[];
}

interface Props {
  objective: string;
  onClose: () => void;
  onExecute: (objective: string) => void;
}

export const PlanPreviewModal: React.FC<Props> = ({ objective, onClose, onExecute }) => {
  const { accessToken } = useStore();
  const [tasks, setTasks] = useState<PreviewTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const res = await fetch(`${DAEMON_URL}/api/v1/dag/preview`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ objective }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setTasks(data.tasks || []);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [objective, accessToken]);

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 200,
      background: 'rgba(0,0,0,0.45)', backdropFilter: 'var(--glass-blur)',
      WebkitBackdropFilter: 'var(--glass-blur)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
    }}>
      <div style={{
        width: '100%', maxWidth: 640, maxHeight: '80vh',
        background: 'var(--bg-elevated)',
        border: '1px solid var(--glass-edge)',
        borderRadius: 16, boxShadow: 'var(--glass-shadow-lg)',
        display: 'flex', flexDirection: 'column',
        animation: 'zoomIn 0.2s var(--ease-spring)',
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid var(--separator)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <GitFork size={16} style={{ color: 'var(--accent-secondary)' }} />
            <div>
              <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: 'var(--text-primary)' }}>Plan Preview</h3>
              <p style={{ margin: 0, fontSize: 10, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                DRY_RUN — NOT EXECUTED
              </p>
            </div>
          </div>
          <button onClick={onClose} className="glass-btn" style={{ padding: '4px 7px' }}>
            <X size={13} />
          </button>
        </div>

        {/* Objective */}
        <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--separator)', background: 'var(--fill-quaternary)' }}>
          <span style={{ fontSize: 9, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.1em', display: 'block', marginBottom: 4 }}>
            OBJECTIVE
          </span>
          <p style={{ margin: 0, fontSize: 13, color: 'var(--text-primary)' }}>{objective}</p>
        </div>

        {/* Task list */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 20px' }} className="scrollbar-hide">
          {loading && (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Loader size={20} className="animate-spin" style={{ color: 'var(--accent)' }} />
              <p style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 10, fontFamily: 'var(--font-mono)', letterSpacing: '0.08em' }}>
                GENERATING_PLAN...
              </p>
            </div>
          )}
          {error && (
            <div style={{ padding: 16, borderRadius: 8, background: 'var(--liquid-danger)', border: '1px solid var(--liquid-danger-edge)', color: 'var(--accent-danger)', fontSize: 12 }}>
              Failed to generate plan: {error}
            </div>
          )}
          {!loading && !error && tasks.map((task, idx) => (
            <div key={task.id} style={{
              padding: '10px 14px', borderRadius: 10, marginBottom: 6,
              background: 'var(--glass-bg)', border: '1px solid var(--glass-edge)',
              display: 'flex', gap: 12, alignItems: 'flex-start',
            }}>
              <div style={{
                width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
                background: 'var(--liquid-secondary)', border: '1px solid var(--liquid-secondary-edge)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 10, fontWeight: 700, fontFamily: 'var(--font-mono)',
                color: 'var(--accent-secondary)',
              }}>
                {idx + 1}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--accent-warm)', textTransform: 'uppercase' }}>
                    {task.action}
                  </span>
                  <span style={{ fontSize: 9, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                    {task.id}
                  </span>
                </div>
                <p style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                  {task.description}
                </p>
                {task.dependencies.length > 0 && (
                  <div style={{ marginTop: 5, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 9, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                      depends on:
                    </span>
                    {task.dependencies.map(d => (
                      <span key={d} style={{
                        fontSize: 9, fontFamily: 'var(--font-mono)',
                        padding: '1px 5px', borderRadius: 3,
                        background: 'var(--fill-quaternary)', border: '1px solid var(--separator)',
                        color: 'var(--text-secondary)',
                      }}>
                        {d}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        {!loading && !error && (
          <div style={{
            padding: '12px 20px', borderTop: '1px solid var(--separator)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <span style={{ fontSize: 11, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
              {tasks.length} task{tasks.length !== 1 ? 's' : ''} · preview only
            </span>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={onClose} className="glass-btn" style={{ padding: '8px 14px', fontSize: 12 }}>
                Discard
              </button>
              <button
                onClick={() => onExecute(objective)}
                className="glass-btn glass-btn--primary"
                style={{ padding: '8px 16px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}
              >
                <Play size={11} /> Execute Plan
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
