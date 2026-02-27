import React from 'react';

type InputType = 'slider' | 'toggle';

interface PersonalityFieldProps {
  label: string;
  type: InputType;
  value: number | string;
  options?: string[]; // For toggles
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
    <div className="flex flex-col gap-2 p-4 border border-zinc/10 bg-zinc/5 transition-all duration-300 hover:border-agent/30">
      <div className="flex justify-between items-center">
        <span className="baunk-style text-[9px] text-zinc-400 tracking-widest">{label}</span>
        {type === 'slider' && (
          <span className="font-mono text-[9px] text-agent">{(value as number).toFixed(2)}</span>
        )}
      </div>
      
      {type === 'slider' ? (
        <div className="relative h-4 flex items-center">
          <input 
            type="range" 
            min="0" 
            max="1" 
            step="0.01" 
            value={value as number}
            onChange={(e) => onChange(parseFloat(e.target.value))}
            className="w-full h-[2px] bg-zinc/20 appearance-none cursor-pointer accent-agent hover:accent-emerald-400 transition-all focus:outline-none"
          />
        </div>
      ) : (
        <div className="flex gap-1 bg-zinc/10 p-1">
          {options.map((opt) => (
            <button
              key={opt}
              onClick={() => onChange(opt)}
              className={`flex-1 py-1.5 text-[8px] baunk-style transition-all duration-300 ${
                value === opt 
                  ? 'bg-agent text-black shadow-md' 
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              {opt}
            </button>
          ))}
        </div>
      )}
      
      <p className="text-[8px] font-mono text-zinc-500 leading-tight min-h-[1.5em]">
        {description}
      </p>
    </div>
  );
};

export default PersonalityField;
