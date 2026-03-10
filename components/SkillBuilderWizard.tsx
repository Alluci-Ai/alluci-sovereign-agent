import React, { useState } from 'react';
import { PolytopeIdentity } from './Identity';
import PersonalityField from './PersonalityField';
import { SkillManifest } from '../types';
import { useStore } from '../store/useStore';

const DAEMON_URL = 'http://localhost:8000';

interface StepProps {
  data: Partial<SkillManifest>;
  update: (key: string, value: any) => void;
  next: () => void;
  back?: () => void;
}

const ListInput: React.FC<{
  items: string[];
  onChange: (items: string[]) => void;
  placeholder: string;
  label: string;
}> = ({ items = [], onChange, placeholder, label }) => {
  const [val, setVal] = useState('');

  const add = () => {
    if (val.trim()) {
      onChange([...items, val.trim()]);
      setVal('');
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <span className="glass-label text-[8px] opacity-60 tracking-widest">{label}</span>
      <div className="flex flex-wrap gap-2 mb-1">
        {items.map((item, i) => (
          <span key={i} className="bg-white/5 border border-[rgba(255,255,255,0.08)] px-2 py-1 text-text-primary rounded-sm">
            {item}
            <button onClick={() => onChange(items.filter((_, idx) => idx !== i))} className="text-red-400 hover:text-red-600 font-bold ml-1">×</button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          className="glass-input w-full"
          value={val}
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && add()}
          placeholder={placeholder}
        />
        <button onClick={add} className="glass-btn px-4 shrink-0" style={{ background: 'var(--liquid-accent)', border: '0.5px solid var(--liquid-accent-edge)', color: 'var(--accent)' }}>+</button>
      </div>
    </div>
  );
};

const StepMetadata: React.FC<StepProps> = ({ data, update, next }) => {
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result;
      if (typeof content === 'string') {
        update('instructions', content);
      }
    };
    reader.readAsText(file);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="flex flex-col gap-6 animate-in slide-in-from-right-4">
      <h3 className="glass-label text-[12px] border-b border-sovereign pb-1 mb-4">1. METADATA_LAYER</h3>

      <div className="flex flex-col gap-2">
        <label className="glass-label text-[8px] opacity-60">MODULE_NAME</label>
        <input
          className="glass-input w-full"
          value={data.name || ''}
          onChange={(e) => {
            update('name', e.target.value);
            if (!data.id) update('id', e.target.value.toLowerCase().replace(/\s+/g, '_') + '_' + Math.floor(Math.random() * 1000));
          }}
          placeholder="e.g. Quantum Reasoning v1"
        />
      </div>

      <div className="flex flex-col gap-2">
        <label className="glass-label text-[8px] opacity-60">UNIQUE_IDENTIFIER</label>
        <input
          className="glass-input w-full"
          value={data.id || ''}
          onChange={(e) => update('id', e.target.value)}
        />
      </div>

      <div className="flex flex-col gap-2">
        <label className="glass-label text-[8px] opacity-60">CATEGORY</label>
        <select
          className="glass-input w-full"
          value={data.category || 'CUSTOM'}
          onChange={(e) => update('category', e.target.value)}
        >
          <option value="CUSTOM">CUSTOM_MODULE</option>
          <option value="FRAMEWORK">FRAMEWORK</option>
          <option value="BRIDGE">BRIDGE_ADAPTER</option>
        </select>
      </div>

      <div className="flex flex-col gap-2">
        <label className="glass-label text-[8px] opacity-60">DESCRIPTION</label>
        <textarea
          className="glass-input w-full min-h-[60px]"
          value={data.description || ''}
          onChange={(e) => update('description', e.target.value)}
          placeholder="Define the purpose and scope of this cognitive module..."
        />
      </div>

      <div className="w-full border-b border-[rgba(255,255,255,0.08)] my-4" />
      <h4 className="glass-label text-[10px] opacity-40 mb-2">MODULE_INSTRUCTIONS</h4>

      <div className="flex flex-col gap-2">
        <div className="flex justify-between items-center">
          <label className="glass-label text-[8px] opacity-60">RAW SYSTEM PROMPT (.MD)</label>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="glass-btn text-[9px] px-3 py-1 bg-white/5 border border-white/10"
          >
            UPLOAD .MD FILE
          </button>
          <input
            type="file"
            accept=".md,.txt"
            ref={fileInputRef}
            style={{ display: 'none' }}
            onChange={handleFileUpload}
          />
        </div>
        <textarea
          className="glass-input w-full min-h-[160px] font-mono text-[11px]"
          value={data.instructions || ''}
          onChange={(e) => update('instructions', e.target.value)}
          placeholder="Paste markdown instructions here or upload a .md file..."
        />
      </div>

      <div className="w-full border-b border-[rgba(255,255,255,0.08)] my-4" />
      <h4 className="glass-label text-[10px] opacity-40 mb-2">EXTENDED_META_PROPERTIES</h4>

      <ListInput
        label="1. MINDSETS"
        items={data.mindsets || []}
        onChange={(i) => update('mindsets', i)}
        placeholder="e.g. 'Growth', 'Skeptical'"
      />

      <ListInput
        label="2. METHODOLOGIES"
        items={data.methodologies || []}
        onChange={(i) => update('methodologies', i)}
        placeholder="e.g. 'First Principles', 'Socratic'"
      />

      <div className="flex flex-col gap-4 p-3  border border-zinc/10 mt-2">
        <span className="glass-label text-[8px] opacity-60 tracking-widest">3. COGNITIVE_CHAINS_&_LOGIC</span>

        <ListInput
          label="LOGIC_AXIOMS"
          items={data.logic || []}
          onChange={(i) => update('logic', i)}
          placeholder="e.g. 'If X then Y'"
        />

        <ListInput
          label="CHAIN_OF_THOUGHT"
          items={data.chainsOfThought || []}
          onChange={(i) => update('chainsOfThought', i)}
          placeholder="Step-by-step reasoning..."
        />
      </div>

      <div className="mt-2">
        <ListInput
          label="4. BEST_PRACTICES_GUIDE"
          items={data.bestPractices || []}
          onChange={(i) => update('bestPractices', i)}
          placeholder="e.g. 'Always verify output integrity'"
        />
      </div>

      <div className="flex justify-end mt-4">
        <button onClick={next} disabled={!data.name} className="glass-btn glass-btn--primary glass-label text-[9px] px-6 disabled:opacity-50">
          [ NEXT: COGNITION ] →
        </button>
      </div>
    </div>
  );
};

const StepCognition: React.FC<StepProps> = ({ data, update, next, back }) => (
  <div className="flex flex-col gap-6 animate-in slide-in-from-right-4">
    <h3 className="glass-label text-[12px] border-b border-sovereign pb-1 mb-4">2. COGNITIVE_ARCHITECTURE</h3>

    <div className="p-4  border border-zinc/10 mb-2">
      <p className="text-[9px] font-mono opacity-60">
        Configure the declarative knowledge base for this module. Mindsets and Logic have been moved to the Metadata Layer.
      </p>
    </div>

    <ListInput
      label="KNOWLEDGE_DOMAINS"
      items={data.knowledge || []}
      onChange={(i) => update('knowledge', i)}
      placeholder="Add knowledge block (e.g. 'Game Theory')..."
    />

    <div className="flex justify-between mt-4">
      <button onClick={back} className="glass-btn glass-label text-[9px] px-6">← [ BACK ]</button>
      <button onClick={next} className="glass-btn glass-btn--primary glass-label text-[9px] px-6">
        [ NEXT: STRATEGY ] →
      </button>
    </div>
  </div>
);

const StepReasoning: React.FC<StepProps> = ({ data, update, next, back }) => (
  <div className="flex flex-col gap-6 animate-in slide-in-from-right-4">
    <h3 className="glass-label text-[12px] border-b border-sovereign pb-1 mb-4">3. REASONING_STRATEGY</h3>

    <div className="p-4  border border-zinc/10 mb-2">
      <p className="text-[9px] font-mono opacity-60">
        Define high-level strategic frameworks. Methodologies and Chain of Thought have been moved to the Metadata Layer.
      </p>
    </div>

    <ListInput
      label="FRAMEWORKS"
      items={data.frameworks || []}
      onChange={(i) => update('frameworks', i)}
      placeholder="Add structural framework (e.g. 'SWOT')..."
    />

    <div className="flex justify-between mt-4">
      <button onClick={back} className="glass-btn glass-label text-[9px] px-6">← [ BACK ]</button>
      <button onClick={next} className="glass-btn glass-btn--primary glass-label text-[9px] px-6">
        [ CALIBRATE_VECTORS ] →
      </button>
    </div>
  </div>
);

const StepCalibration: React.FC<Omit<StepProps, 'next'> & { onSave: () => void }> = ({ data, update, back, onSave }) => (
  <div className="flex flex-col gap-6 animate-in slide-in-from-right-4">
    <h3 className="glass-label text-[12px] border-b border-sovereign pb-1 mb-4">4. PERSONALITY_VECTOR_MAPPING</h3>

    <div className="flex flex-col gap-4 p-4 border border-[rgba(255,255,255,0.08)] mt-2">
      Define how this skill shifts the agent's baseline personality when active.
      Values range from -1.0 (Decrease) to +1.0 (Increase).
    </div>

    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <PersonalityField
        label="TONE_SHIFT"
        type="slider"
        value={data.personalityMapping?.toneShift || 0}
        onChange={(v) => update('personalityMapping', { ...data.personalityMapping, toneShift: v })}
        description="-1.0 (Casual) ↔ +1.0 (Formal)"
      />
      <PersonalityField
        label="ASSERTIVENESS_SHIFT"
        type="slider"
        value={data.personalityMapping?.assertivenessShift || 0}
        onChange={(v) => update('personalityMapping', { ...data.personalityMapping, assertivenessShift: v })}
        description="-1.0 (Passive) ↔ +1.0 (Direct)"
      />
      <PersonalityField
        label="CREATIVITY_SHIFT"
        type="slider"
        value={data.personalityMapping?.creativityShift || 0}
        onChange={(v) => update('personalityMapping', { ...data.personalityMapping, creativityShift: v })}
        description="-1.0 (Logical) ↔ +1.0 (Divergent)"
      />
      <PersonalityField
        label="EMPATHY_SHIFT"
        type="slider"
        value={data.personalityMapping?.empathyShift || 0}
        onChange={(v) => update('personalityMapping', { ...data.personalityMapping, empathyShift: v })}
        description="-1.0 (Robotic) ↔ +1.0 (Affective)"
      />
    </div>

    <div className="flex justify-between mt-8">
      <button onClick={back} className="glass-btn glass-label text-[9px] px-6">← [ BACK ]</button>
      <button onClick={onSave} className="glass-btn glass-btn--primary glass-label text-[9px] px-8">
        [ COMPILE_&_SAVE_MODULE ]
      </button>
    </div>
  </div>
);

const SkillBuilderWizard: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const token = useStore(state => state.accessToken);
  const [step, setStep] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [manifest, setManifest] = useState<Partial<SkillManifest>>({
    knowledge: [],
    mindsets: [],
    methodologies: [],
    frameworks: [],
    chainsOfThought: [],
    logic: [],
    bestPractices: [],
    personalityMapping: { toneShift: 0, creativityShift: 0, assertivenessShift: 0, empathyShift: 0 },
    verified: true,
    capabilities: []
  });

  const update = (key: string, value: any) => {
    setManifest(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setIsSaving(true);

    try {
      // 1. Get real cryptographic signature from the backend
      const signRes = await fetch(`${DAEMON_URL}/api/skill/sign`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify(manifest)
      });

      if (!signRes.ok) {
        throw new Error("Failed to sign skill manifest. Ensure the Sovereign Vault is unlocked.");
      }

      const { signature, hash, signer } = await signRes.json();

      // 2. Finalize object with real signature
      const payload = {
        ...manifest,
        signature: signature,
        hash: hash,
        signer: signer,
        publicKey: "pub_local_vault"
      };

      const res = await fetch(`${DAEMON_URL}/skills`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        onClose();
      } else {
        alert("Failed to save to Daemon. Is it running?");
      }
    } catch (e: any) {
      console.error(e);
      alert(e.message || "Network Error: Could not connect to Sovereign Daemon.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex flex-col h-full relative">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-sovereign pb-6 mb-6">
        <div className="flex items-center gap-4">
          <div className="p-2 border border-black text-black">
            <PolytopeIdentity size={24} color="#000" />
          </div>
          <div className="flex flex-col">
            <h2 className="glass-label text-lg tracking-[0.3em]">COGNITIVE_MODULE_BUILDER</h2>
            <span className="text-[8px] font-mono opacity-40">Step {step + 1} of 4</span>
          </div>
        </div>
        <button onClick={onClose} className="p-2 text-text-tertiary hover:text-text-primary transition-colors">
          <span className="text-xl">✕</span>
        </button>
      </div>

      {/* Progress Bar */}
      <div className="flex gap-1 mb-6 h-1 w-full overflow-hidden" style={{ background: 'var(--fill-quaternary)', borderRadius: 2 }}>
        {[0, 1, 2, 3].map(i => (
          <div key={i} className="flex-1 transition-all duration-500" style={{ background: i <= step ? 'var(--liquid-accent)' : 'transparent', backdropFilter: i <= step ? 'blur(4px)' : 'none', borderRadius: 2 }} />
        ))}
      </div>

      {/* Wizard Content & Sidebar Container */}
      <div className="flex-1 relative overflow-hidden flex">

        {/* Main Steps */}
        <div className="flex-1 overflow-y-auto scrollbar-hide pb-20 lg:pr-[33%] h-full">
          {step === 0 && <StepMetadata data={manifest} update={update} next={() => setStep(1)} />}
          {step === 1 && <StepCognition data={manifest} update={update} next={() => setStep(2)} back={() => setStep(0)} />}
          {step === 2 && <StepReasoning data={manifest} update={update} next={() => setStep(3)} back={() => setStep(1)} />}
          {step === 3 && <StepCalibration data={manifest} update={update} back={() => setStep(2)} onSave={handleSave} />}
        </div>

        {/* JSON Preview Sidebar (Desktop Only) */}
        <div className="hidden lg:block absolute top-0 right-0 w-1/3 h-full border-l border-[rgba(255,255,255,0.18)]  p-6 overflow-hidden">
          <h4 className="glass-label text-[8px] opacity-40 mb-4">LIVE_MANIFEST_PREVIEW</h4>
          <pre className="text-[8px] font-mono overflow-auto h-full pb-10 opacity-70">
            {JSON.stringify(manifest, null, 2)}
          </pre>
        </div>
      </div>

      {isSaving && (
        <div className="absolute inset-0 z-50 backdrop-blur-sm flex items-center justify-center" style={{ background: 'rgba(28,28,30,0.85)' }}>
          <div className="glass-label" style={{ color: 'var(--accent)', animation: 'acePulse 2s ease infinite' }}>COMPILING_COGNITIVE_STRUCTURE...</div>
        </div>
      )}
    </div>
  );
};

export default SkillBuilderWizard;