import React, { useState } from 'react';
import { PolytopeIdentity } from './App';
import PersonalityField from './PersonalityField';
import { SkillManifest } from './types';

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
      <span className="baunk-style text-[8px] opacity-60 tracking-widest">{label}</span>
      <div className="flex flex-wrap gap-2 mb-1">
        {items.map((item, i) => (
          <span key={i} className="flex items-center gap-1 bg-zinc/10 border border-zinc/20 px-2 py-1 text-[9px] font-mono">
            {item}
            <button onClick={() => onChange(items.filter((_, idx) => idx !== i))} className="text-red-400 hover:text-red-600 font-bold ml-1">×</button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input 
          className="flex-1 bg-zinc/5 border border-zinc/20 text-[10px] font-mono p-2 focus:outline-none focus:border-agent"
          value={val}
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && add()}
          placeholder={placeholder}
        />
        <button onClick={add} className="bg-zinc/10 px-3 text-[10px] baunk-style hover:bg-agent hover:text-white transition-colors">+</button>
      </div>
    </div>
  );
};

const StepMetadata: React.FC<StepProps> = ({ data, update, next }) => (
  <div className="flex flex-col gap-6 animate-in slide-in-from-right-4">
    <h3 className="baunk-style text-[12px] border-b border-sovereign pb-1 mb-4">1. METADATA_LAYER</h3>
    
    <div className="flex flex-col gap-2">
      <label className="baunk-style text-[8px] opacity-60">MODULE_NAME</label>
      <input 
        className="bg-zinc/5 border border-zinc/20 p-3 text-[10px] font-mono focus:border-agent outline-none"
        value={data.name || ''}
        onChange={(e) => {
          update('name', e.target.value);
          if (!data.id) update('id', e.target.value.toLowerCase().replace(/\s+/g, '_') + '_' + Math.floor(Math.random()*1000));
        }}
        placeholder="e.g. Quantum Reasoning v1"
      />
    </div>

    <div className="flex flex-col gap-2">
      <label className="baunk-style text-[8px] opacity-60">UNIQUE_IDENTIFIER</label>
      <input 
        className="bg-zinc/5 border border-zinc/20 p-3 text-[10px] font-mono focus:border-agent outline-none opacity-60"
        value={data.id || ''}
        onChange={(e) => update('id', e.target.value)}
      />
    </div>

    <div className="flex flex-col gap-2">
      <label className="baunk-style text-[8px] opacity-60">CATEGORY</label>
      <select 
        className="bg-zinc/5 border border-zinc/20 p-3 text-[10px] font-mono focus:border-agent outline-none"
        value={data.category || 'CUSTOM'}
        onChange={(e) => update('category', e.target.value)}
      >
        <option value="CUSTOM">CUSTOM_MODULE</option>
        <option value="FRAMEWORK">FRAMEWORK</option>
        <option value="BRIDGE">BRIDGE_ADAPTER</option>
      </select>
    </div>

    <div className="flex flex-col gap-2">
      <label className="baunk-style text-[8px] opacity-60">DESCRIPTION</label>
      <textarea 
        className="bg-zinc/5 border border-zinc/20 p-3 text-[10px] font-mono focus:border-agent outline-none h-24 resize-none"
        value={data.description || ''}
        onChange={(e) => update('description', e.target.value)}
        placeholder="Define the purpose and scope of this cognitive module..."
      />
    </div>

    <div className="h-px bg-zinc/10 w-full my-4" />
    <h4 className="baunk-style text-[10px] opacity-40 mb-2">EXTENDED_META_PROPERTIES</h4>

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

    <div className="flex flex-col gap-4 p-3 bg-zinc/5 border border-zinc/10 mt-2">
        <span className="baunk-style text-[8px] opacity-60 tracking-widest">3. COGNITIVE_CHAINS_&_LOGIC</span>
        
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
      <button onClick={next} disabled={!data.name} className="alce-button baunk-style text-[9px] px-6 bg-sovereign text-white disabled:opacity-50">
        [ NEXT: COGNITION ] →
      </button>
    </div>
  </div>
);

const StepCognition: React.FC<StepProps> = ({ data, update, next, back }) => (
  <div className="flex flex-col gap-6 animate-in slide-in-from-right-4">
    <h3 className="baunk-style text-[12px] border-b border-sovereign pb-1 mb-4">2. COGNITIVE_ARCHITECTURE</h3>
    
    <div className="p-4 bg-zinc/5 border border-zinc/10 mb-2">
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
      <button onClick={back} className="alce-button baunk-style text-[9px] px-6">← [ BACK ]</button>
      <button onClick={next} className="alce-button baunk-style text-[9px] px-6 bg-sovereign text-white">
        [ NEXT: STRATEGY ] →
      </button>
    </div>
  </div>
);

const StepReasoning: React.FC<StepProps> = ({ data, update, next, back }) => (
  <div className="flex flex-col gap-6 animate-in slide-in-from-right-4">
    <h3 className="baunk-style text-[12px] border-b border-sovereign pb-1 mb-4">3. REASONING_STRATEGY</h3>
    
    <div className="p-4 bg-zinc/5 border border-zinc/10 mb-2">
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
      <button onClick={back} className="alce-button baunk-style text-[9px] px-6">← [ BACK ]</button>
      <button onClick={next} className="alce-button baunk-style text-[9px] px-6 bg-sovereign text-white">
        [ CALIBRATE_VECTORS ] →
      </button>
    </div>
  </div>
);

const StepCalibration: React.FC<Omit<StepProps, 'next'> & { onSave: () => void }> = ({ data, update, back, onSave }) => (
  <div className="flex flex-col gap-6 animate-in slide-in-from-right-4">
    <h3 className="baunk-style text-[12px] border-b border-sovereign pb-1 mb-4">4. PERSONALITY_VECTOR_MAPPING</h3>
    
    <div className="p-4 bg-zinc/5 border border-zinc/20 text-[9px] font-mono mb-4">
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
      <button onClick={back} className="alce-button baunk-style text-[9px] px-6">← [ BACK ]</button>
      <button onClick={onSave} className="alce-button baunk-style text-[9px] px-8 bg-agent text-white hover:bg-emerald-400">
        [ COMPILE_&_SAVE_MODULE ]
      </button>
    </div>
  </div>
);

const SkillBuilderWizard: React.FC<{ onClose: () => void }> = ({ onClose }) => {
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
    const token = localStorage.getItem('alluci_daemon_token');
    
    // Finalize object
    const payload = {
        ...manifest,
        signature: `sig_${Date.now().toString(36)}`, // Client-side stub, backend should handle real signing
        publicKey: "pub_local_client"
    };

    try {
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
    } catch (e) {
        console.error(e);
        alert("Network Error: Could not connect to Sovereign Daemon.");
    } finally {
        setIsSaving(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white relative">
        {/* Header */}
        <div className="flex items-center gap-4 border-b border-sovereign pb-6 mb-6">
            <div className="w-12 h-12 bg-zinc/5 border border-zinc/20 flex items-center justify-center">
                <PolytopeIdentity size={24} color="#000" />
            </div>
            <div className="flex flex-col">
                <h2 className="baunk-style text-lg tracking-[0.3em]">COGNITIVE_MODULE_BUILDER</h2>
                <span className="text-[8px] font-mono opacity-40">Step {step + 1} of 4</span>
            </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full h-1 bg-zinc/10 mb-8 flex">
            {[0, 1, 2, 3].map(i => (
                <div key={i} className={`flex-1 transition-all duration-500 ${i <= step ? 'bg-agent' : 'bg-transparent'}`} />
            ))}
        </div>

        {/* Wizard Content */}
        <div className="flex-1 overflow-y-auto scrollbar-hide pb-20">
            {step === 0 && <StepMetadata data={manifest} update={update} next={() => setStep(1)} />}
            {step === 1 && <StepCognition data={manifest} update={update} next={() => setStep(2)} back={() => setStep(0)} />}
            {step === 2 && <StepReasoning data={manifest} update={update} next={() => setStep(3)} back={() => setStep(1)} />}
            {step === 3 && <StepCalibration data={manifest} update={update} back={() => setStep(2)} onSave={handleSave} />}
        </div>

        {/* JSON Preview Sidebar (Desktop Only) */}
        <div className="hidden lg:block absolute top-0 right-0 w-1/3 h-full border-l border-sovereign/10 bg-zinc/5 p-6 overflow-hidden">
            <h4 className="baunk-style text-[8px] opacity-40 mb-4">LIVE_MANIFEST_PREVIEW</h4>
            <pre className="text-[8px] font-mono overflow-auto h-full pb-10 opacity-70">
                {JSON.stringify(manifest, null, 2)}
            </pre>
        </div>

        {isSaving && (
            <div className="absolute inset-0 bg-white/80 flex items-center justify-center z-50">
                <div className="baunk-style text-agent animate-pulse">COMPILING_COGNITIVE_STRUCTURE...</div>
            </div>
        )}
    </div>
  );
};

export default SkillBuilderWizard;