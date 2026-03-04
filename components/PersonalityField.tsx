import React from 'react';
import GlassSlider from './GlassSlider';

type InputType = 'slider' | 'toggle';

interface PersonalityFieldProps {
  label: string;
  type: InputType;
  value: number | string;
  options?: string[];
  onChange: (val: any) => void;
  description: string;
}

const PersonalityField: React.FC<PersonalityFieldProps> = ({
  label,
  type,
  value,
  options = [],
  onChange,
  description
}) => {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: 6,
      padding: 12,
      border: '1px solid var(--separator)',
      borderRadius: 10,
      background: 'var(--fill-quaternary)',
      transition: 'all 0.2s ease',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{
          fontSize: 11, fontWeight: 600,
          color: 'var(--text-tertiary)',
          letterSpacing: '0.02em',
        }}>{label}</span>
        {type === 'slider' && (
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 11,
            color: 'var(--accent)',
            fontWeight: 500,
          }}>{(value as number).toFixed(2)}</span>
        )}
      </div>

      {type === 'slider' ? (
        <GlassSlider
          value={value as number}
          onChange={onChange}
          accent="var(--accent)"
        />
      ) : (
        <div style={{
          display: 'flex', gap: 2,
          background: 'var(--fill-quaternary)',
          borderRadius: 8,
          padding: 2,
          border: '1px solid var(--separator)',
        }}>
          {options.map((opt) => (
            <button key={opt} onClick={() => onChange(opt)} style={{
              flex: 1, padding: '5px 8px',
              borderRadius: 6,
              fontSize: 10, fontWeight: 500,
              border: value === opt ? '0.5px solid var(--liquid-accent-edge)' : 'none',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
              background: value === opt ? 'var(--liquid-accent)' : 'transparent',
              backdropFilter: value === opt ? 'blur(12px) saturate(150%)' : 'none',
              color: value === opt ? 'var(--accent)' : 'var(--text-tertiary)',
              boxShadow: value === opt ? 'var(--liquid-inner-glow), 0 1px 4px rgba(48, 209, 88, 0.08)' : 'none',
            }}>
              {opt}
            </button>
          ))}
        </div>
      )}

      <p style={{
        fontSize: 10, fontFamily: 'var(--font-mono)',
        color: 'var(--text-quaternary)',
        lineHeight: 1.3, minHeight: '1.2em',
      }}>
        {description}
      </p>
    </div>
  );
};

export default PersonalityField;
