
import React, { useState } from 'react';
import { Play, Eye, Loader } from 'lucide-react';

interface Props {
  onSubmit: (objective: string, autonomy: string) => Promise<void>;
  onPreview: (objective: string) => void;
}

export const ObjectiveSubmitBar: React.FC<Props> = ({ onSubmit, onPreview }) => {
  const [objective, setObjective] = useState('');
  const [autonomy, setAutonomy] = useState('SEMI_AUTONOMOUS');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!objective.trim() || submitting) return;
    setSubmitting(true);
    try {
      await onSubmit(objective.trim(), autonomy);
      setObjective('');
    } finally {
      setSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit();
  };

  return (
    <div style={{
      padding: '12px 14px', borderBottom: '1px solid var(--separator)',
      background: 'var(--glass-bg)',
      backdropFilter: 'var(--glass-blur)',
      WebkitBackdropFilter: 'var(--glass-blur)',
    }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
        <div style={{ flex: 1 }}>
          <span style={{
            fontSize: 9, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)',
            textTransform: 'uppercase', letterSpacing: '0.1em', display: 'block', marginBottom: 5,
          }}>
            NEW_OBJECTIVE
          </span>
          <textarea
            value={objective}
            onChange={e => setObjective(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe what you want the agent to accomplish..."
            rows={2}
            className="glass-input"
            style={{
              width: '100%', resize: 'none', fontSize: 12, lineHeight: 1.5,
              fontFamily: 'inherit', padding: '8px 10px',
            }}
          />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flexShrink: 0 }}>
          <select
            value={autonomy}
            onChange={e => setAutonomy(e.target.value)}
            className="glass-input"
            style={{ fontSize: 10, fontFamily: 'var(--font-mono)', padding: '4px 6px' }}
          >
            <option value="UNRESTRICTED">UNRESTRICTED</option>
            <option value="SEMI_AUTONOMOUS">SEMI_AUTO</option>
            <option value="RESTRICTED">RESTRICTED</option>
          </select>
          <div style={{ display: 'flex', gap: 5 }}>
            <button
              onClick={() => objective.trim() && onPreview(objective.trim())}
              disabled={!objective.trim()}
              className="glass-btn"
              title="Preview plan (dry run)"
              style={{ padding: '7px 10px', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}
            >
              <Eye size={12} /> Preview
            </button>
            <button
              onClick={handleSubmit}
              disabled={!objective.trim() || submitting}
              className="glass-btn glass-btn--primary"
              style={{ padding: '7px 12px', display: 'flex', alignItems: 'center', gap: 5, fontSize: 11 }}
            >
              {submitting ? <Loader size={11} className="animate-spin" /> : <Play size={11} />}
              Execute
            </button>
          </div>
        </div>
      </div>
      <p style={{ fontSize: 9, color: 'var(--text-tertiary)', margin: '6px 0 0', fontFamily: 'var(--font-mono)' }}>
        ⌘↵ to execute · Preview shows DAG without running
      </p>
    </div>
  );
};
