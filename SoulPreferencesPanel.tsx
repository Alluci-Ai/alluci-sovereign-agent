
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { PolytopeIdentity } from './App';
import PersonalityField from './PersonalityField';
import { SoulPreferences, SoulHumor, SoulConciseness, SoulManifest, SkillManifest } from './types';
import SkillBuilderWizard from './SkillBuilderWizard';
import { SKILL_DATABASE } from './knowledge';

const DAEMON_URL = 'http://localhost:8000';

// Custom Radar Chart Component (SVG)
const RadarChart: React.FC<{ preferences: SoulPreferences }> = ({ preferences }) => {
  const size = 160;
  const center = size / 2;
  const radius = (size / 2) - 10;
  
  // Axes: Tone, Assertiveness, Empathy, Creativity, Conciseness (mapped)
  const keys: (keyof SoulPreferences)[] = ['tone', 'assertiveness', 'empathy', 'creativity'];
  const values = keys.map(k => preferences[k] as number);
  
  const angleSlice = (Math.PI * 2) / keys.length;
  
  const points = values.map((val, i) => {
    const angle = i * angleSlice - (Math.PI / 2); // Start at top
    return [
      center + (radius * val * Math.cos(angle)),
      center + (radius * val * Math.sin(angle))
    ];
  });
  
  const polyPoints = points.map(p => p.join(',')).join(' ');

  return (
    <div className="relative w-40 h-40 flex items-center justify-center">
        <svg width={size} height={size} className="overflow-visible">
            {/* Background Grid */}
            <circle cx={center} cy={center} r={radius} fill="none" stroke="#2a2a2a" strokeWidth="0.5" />
            <circle cx={center} cy={center} r={radius * 0.5} fill="none" stroke="#2a2a2a" strokeWidth="0.5" />
            {/* Axes */}
            {points.map((_, i) => {
                const angle = i * angleSlice - (Math.PI / 2);
                return (
                    <line 
                        key={i}
                        x1={center} y1={center}
                        x2={center + radius * Math.cos(angle)}
                        y2={center + radius * Math.sin(angle)}
                        stroke="#2a2a2a" strokeWidth="0.5"
                    />
                );
            })}
            {/* Data Polygon */}
            <polygon points={polyPoints} fill="rgba(145, 214, 95, 0.2)" stroke="#91D65F" strokeWidth="1.5" />
            {/* Points */}
            {points.map((p, i) => (
                <circle key={i} cx={p[0]} cy={p[1]} r="2" fill="#91D65F" />
            ))}
        </svg>
        {/* Labels */}
        <div className="absolute top-0 text-[8px] baunk-style text-agent -mt-4">TONE</div>
        <div className="absolute right-0 text-[8px] baunk-style text-agent -mr-6">ASRT</div>
        <div className="absolute bottom-0 text-[8px] baunk-style text-agent -mb-4">EMPY</div>
        <div className="absolute left-0 text-[8px] baunk-style text-agent -ml-6">CREA</div>
    </div>
  );
};

const TagInput: React.FC<{ 
    label: string; 
    items: string[]; 
    onChange: (items: string[]) => void; 
    placeholder: string;
}> = ({ label, items, onChange, placeholder }) => {
    const [val, setVal] = useState('');
    const add = () => { if(val.trim()){ onChange([...items, val.trim()]); setVal(''); } };
    return (
        <div className="space-y-2">
            <label className="text-[9px] baunk-style opacity-60 block">{label}</label>
            <div className="flex flex-wrap gap-2">
                {items.map((it, i) => (
                    <span key={i} className="bg-zinc/5 border border-zinc/10 px-2 py-1 text-[9px] font-mono flex items-center gap-2">
                        {it}
                        <button onClick={() => onChange(items.filter((_, idx) => idx !== i))} className="text-red-400 hover:text-red-500">×</button>
                    </span>
                ))}
            </div>
            <div className="flex gap-2">
                <input 
                    className="flex-1 bg-zinc/5 border border-zinc/20 p-2 text-[9px] font-mono outline-none focus:border-agent"
                    value={val}
                    onChange={e => setVal(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && add()}
                    placeholder={placeholder}
                />
                <button onClick={add} className="bg-zinc/10 px-3 text-[10px] hover:bg-agent hover:text-white">+</button>
            </div>
        </div>
    );
};

const IdentityForge: React.FC<{ onClose: () => void; onManifestUpdate?: (manifest: SoulManifest) => void }> = ({ onClose, onManifestUpdate }) => {
  const [tab, setTab] = useState<'IDENTITY' | 'COGNITION'>('IDENTITY');
  const [manifest, setManifest] = useState<SoulManifest | null>(null);
  const [loading, setLoading] = useState(true);
  const [isDirty, setIsDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  // Skill Ingestion State
  const [isSkillPickerOpen, setIsSkillPickerOpen] = useState(false);
  const [selectedSkillsForIngest, setSelectedSkillsForIngest] = useState<string[]>([]);

  const fetchManifest = async () => {
    const token = localStorage.getItem('alluci_daemon_token');
    try {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), 1000); // Short timeout for local check
        
        const res = await fetch(`${DAEMON_URL}/soul/manifest`, {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {},
            signal: controller.signal
        });
        clearTimeout(id);

        if (res.ok) {
            setManifest(await res.json());
            setLoading(false);
            return;
        }
        throw new Error("Failed to load from Daemon");
    } catch(e) { 
        console.warn("Daemon unreachable, checking local cache.");
        const cached = localStorage.getItem('alluci_soul_manifest');
        if (cached) {
            try {
                setManifest(JSON.parse(cached));
                setLoading(false);
                return;
            } catch(err) { console.error("Cache corrupted"); }
        }

        // Default Fallback
        setManifest({
            preferences: {
                tone: 0.5,
                humor: SoulHumor.DRY,
                empathy: 0.5,
                assertiveness: 0.5,
                creativity: 0.5,
                verbosity: 0.5,
                conciseness: SoulConciseness.BALANCED
            },
            identityCore: "OFFLINE_MODE: You are Alluci, a Sovereign Executive Assistant operating within a high-dimensional Polytope geometry.",
            directives: ["Sovereignty", "Polytopic Reasoning", "Deterministic Execution"],
            voiceProfile: "Professional, crisp, slightly futuristic, yet warm.",
            reasoningStyle: "Polytopic Method: Vertex Identification, Edge Mapping, Face Selection, Collapse.",
            knowledgeGraph: ["Circular Economy", "Value Based Pricing", "Verus Ecosystem"],
            frameworks: ["Business Model Canvas", "First Principles"],
            mindsets: ["Growth", "Sovereign"],
            methodologies: ["First Principles"],
            chainsOfThought: ["Identify Variables -> Map Edges -> Solve"],
            logic: ["Waste is data in the wrong place"],
            bestPractices: ["Verify inputs"],
            bootSequence: "LOADING OFFLINE COGNITION LAYER...",
            heartbeat: "- [x] Monitor system vitality\n- [ ] Sync offline caches",
            executionGraph: { nodes: [], edges: [] }
        });
        setLoading(false);
    }
  };

  useEffect(() => { fetchManifest(); }, []);

  const updateManifest = (key: keyof SoulManifest, val: any) => {
    if (!manifest) return;
    setManifest({ ...manifest, [key]: val });
    setIsDirty(true);
  };

  const updatePrefs = (key: keyof SoulPreferences, val: any) => {
    if (!manifest) return;
    setManifest({ ...manifest, preferences: { ...manifest.preferences, [key]: val } });
    setIsDirty(true);
  };

  const commitChanges = async () => {
    if (!manifest) return;
    setSaving(true);
    const token = localStorage.getItem('alluci_daemon_token');
    
    try {
        const res = await fetch(`${DAEMON_URL}/soul/manifest`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...(token ? { 'Authorization': `Bearer ${token}` } : {}) },
            body: JSON.stringify(manifest)
        });
        
        if (res.ok) {
            setIsDirty(false);
        } else if (res.status === 429) {
            alert("IDENTITY_FORGE_LOCKED: Biometric stress detected. Calm down to proceed.");
            throw new Error("Throttled");
        } else {
            throw new Error("Backend Error");
        }
    } catch(e) { 
        console.warn("Daemon offline/error, saving to local manifold cache.");
        // Fallback Persistence
        localStorage.setItem('alluci_soul_manifest', JSON.stringify(manifest));
        setIsDirty(false);
    } finally { 
        // Always update runtime state regardless of backend status
        if (onManifestUpdate) onManifestUpdate(manifest);
        setSaving(false); 
    }
  };

  const handleIngestSkills = () => {
    if (!manifest) return;
    const skillsToIngest = SKILL_DATABASE.filter(s => selectedSkillsForIngest.includes(s.id));
    
    const newManifest = { ...manifest };
    const addUnique = (arr: string[], items: string[] | undefined) => {
        if (!items) return arr;
        items.forEach(item => {
            if (!arr.includes(item)) arr.push(item);
        });
        return arr;
    };

    skillsToIngest.forEach(skill => {
        // Hydrate Knowledge Graph (Active Domains)
        if (!newManifest.knowledgeGraph.includes(skill.name)) {
            newManifest.knowledgeGraph.push(skill.name);
        }
        newManifest.knowledgeGraph = addUnique(newManifest.knowledgeGraph, skill.knowledge);

        // Hydrate Cognitive Properties
        newManifest.frameworks = addUnique(newManifest.frameworks, skill.frameworks);
        newManifest.mindsets = addUnique(newManifest.mindsets, skill.mindsets);
        newManifest.methodologies = addUnique(newManifest.methodologies, skill.methodologies);
        newManifest.chainsOfThought = addUnique(newManifest.chainsOfThought, skill.chainsOfThought);
        newManifest.logic = addUnique(newManifest.logic, skill.logic);
        newManifest.bestPractices = addUnique(newManifest.bestPractices, skill.bestPractices);
    });

    setManifest(newManifest);
    setIsDirty(true);
    setIsSkillPickerOpen(false);
    setSelectedSkillsForIngest([]);
  };

  if (loading || !manifest) return <div className="p-10 baunk-style text-[10px] animate-pulse">LOADING_IDENTITY_MATRIX...</div>;

  return (
    <div className="flex flex-col h-full bg-white relative">
        {/* Top Bar */}
        <div className="flex justify-between items-center border-b border-sovereign pb-4 mb-6 shrink-0">
             <div className="flex gap-6">
                 {['IDENTITY', 'COGNITION'].map((t) => (
                     <button 
                       key={t}
                       onClick={() => setTab(t as any)}
                       className={`baunk-style text-[10px] pb-2 border-b-2 transition-all ${tab === t ? 'border-agent text-black' : 'border-transparent text-zinc hover:text-black'}`}
                     >
                        {t}_LAYER
                     </button>
                 ))}
             </div>
             <div className="flex items-center gap-4">
                 {isDirty && <span className="text-[8px] baunk-style text-tension animate-pulse">UNSAVED_CHANGES</span>}
                 <button 
                   onClick={commitChanges}
                   disabled={saving}
                   className="alce-button baunk-style text-[9px] px-6 bg-sovereign text-white hover:bg-agent disabled:opacity-50"
                 >
                    {saving ? '[ COMMITTING... ]' : '[ COMMIT_SOUL ]'}
                 </button>
             </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto scrollbar-hide pb-20 relative">
            
            {/* 1. IDENTITY MATRIX */}
            {tab === 'IDENTITY' && (
                <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
                    {/* Visualizer */}
                    <div className="md:col-span-4 bg-zinc/5 border border-sovereign/10 p-8 flex flex-col items-center justify-center gap-8">
                        <RadarChart preferences={manifest.preferences} />
                        <div className="text-center space-y-2">
                             <h4 className="baunk-style text-[10px]">SOUL_SIGNATURE_HASH</h4>
                             <p className="font-mono text-[8px] opacity-40 break-all">{manifest.preferences.tone * 999123 | 0}_X9</p>
                        </div>
                    </div>

                    {/* Editors */}
                    <div className="md:col-span-8 space-y-8">
                         <div className="space-y-4">
                            <h3 className="baunk-style text-[10px] opacity-40 border-b border-zinc/10 pb-2">CORE_PARAMETERS</h3>
                            <div className="grid grid-cols-2 gap-4">
                                <PersonalityField label="TONE" type="slider" value={manifest.preferences.tone} onChange={v => updatePrefs('tone', v)} description="0: Casual ↔ 1: Formal" />
                                <PersonalityField label="EMPATHY" type="slider" value={manifest.preferences.empathy} onChange={v => updatePrefs('empathy', v)} description="Validation weight" />
                                <PersonalityField label="ASSERTIVENESS" type="slider" value={manifest.preferences.assertiveness} onChange={v => updatePrefs('assertiveness', v)} description="Directive strength" />
                                <PersonalityField label="CREATIVITY" type="slider" value={manifest.preferences.creativity} onChange={v => updatePrefs('creativity', v)} description="Divergence" />
                            </div>
                         </div>

                         <div className="space-y-4">
                            <h3 className="baunk-style text-[10px] opacity-40 border-b border-zinc/10 pb-2">NARRATIVE_PILLARS</h3>
                            <div className="space-y-4">
                                <div>
                                    <label className="text-[9px] baunk-style opacity-60 block mb-2">IDENTITY_CORE</label>
                                    <textarea 
                                        className="w-full h-24 bg-zinc/5 border border-zinc/20 p-3 text-[10px] font-mono focus:border-agent outline-none resize-none"
                                        value={manifest.identityCore}
                                        onChange={e => updateManifest('identityCore', e.target.value)}
                                    />
                                </div>
                                <div>
                                    <label className="text-[9px] baunk-style opacity-60 block mb-2">HEARTBEAT_ORDERS</label>
                                    <textarea 
                                        className="w-full h-24 bg-zinc/5 border border-zinc/20 p-3 text-[10px] font-mono focus:border-agent outline-none resize-none"
                                        value={manifest.heartbeat || ''}
                                        onChange={e => updateManifest('heartbeat', e.target.value)}
                                        placeholder="- [x] Monitor system vitality..."
                                    />
                                </div>
                                <div>
                                    <label className="text-[9px] baunk-style opacity-60 block mb-2">VOICE_PROFILE</label>
                                    <input 
                                        className="w-full bg-zinc/5 border border-zinc/20 p-3 text-[10px] font-mono focus:border-agent outline-none"
                                        value={manifest.voiceProfile}
                                        onChange={e => updateManifest('voiceProfile', e.target.value)}
                                    />
                                </div>
                                <TagInput 
                                    label="PRIME_DIRECTIVES" 
                                    items={manifest.directives} 
                                    onChange={i => updateManifest('directives', i)} 
                                    placeholder="Add directive..." 
                                />
                            </div>
                         </div>
                    </div>
                </div>
            )}

            {/* 2. COGNITION LAYER */}
            {tab === 'COGNITION' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 relative">
                    <div className="space-y-6">
                        <h3 className="baunk-style text-[12px] text-agent">STRUCTURAL_LOGIC</h3>
                        
                        <div>
                            <label className="text-[9px] baunk-style opacity-60 block mb-2">REASONING_STYLE</label>
                            <textarea 
                                className="w-full h-32 bg-zinc/5 border border-zinc/20 p-3 text-[10px] font-mono focus:border-agent outline-none resize-none"
                                value={manifest.reasoningStyle}
                                onChange={e => updateManifest('reasoningStyle', e.target.value)}
                            />
                        </div>

                        <TagInput 
                            label="FRAMEWORKS" 
                            items={manifest.frameworks} 
                            onChange={i => updateManifest('frameworks', i)} 
                            placeholder="Add mental model..." 
                        />

                         <TagInput 
                            label="MINDSETS" 
                            items={manifest.mindsets} 
                            onChange={i => updateManifest('mindsets', i)} 
                            placeholder="Add attitude..." 
                        />

                        <TagInput 
                            label="METHODOLOGIES" 
                            items={manifest.methodologies || []} 
                            onChange={i => updateManifest('methodologies', i)} 
                            placeholder="Add procedural template..." 
                        />

                        <TagInput 
                            label="COGNITIVE_CHAINS" 
                            items={manifest.chainsOfThought || []} 
                            onChange={i => updateManifest('chainsOfThought', i)} 
                            placeholder="Add chain step..." 
                        />

                        <TagInput 
                            label="LOGIC_AXIOMS" 
                            items={manifest.logic || []} 
                            onChange={i => updateManifest('logic', i)} 
                            placeholder="Add axiom..." 
                        />

                        <TagInput 
                            label="BEST_PRACTICES" 
                            items={manifest.bestPractices || []} 
                            onChange={i => updateManifest('bestPractices', i)} 
                            placeholder="Add standard..." 
                        />
                    </div>

                    <div className="space-y-6 flex flex-col">
                        <h3 className="baunk-style text-[12px] text-flux">KNOWLEDGE_GRAPH</h3>
                        <div className="p-6 bg-zinc/5 border border-zinc/10 flex-1 flex flex-col relative gap-6">
                            
                            {/* Active Domains & Import Button */}
                            <div className="space-y-3">
                                <TagInput 
                                    label="ACTIVE_DOMAINS" 
                                    items={manifest.knowledgeGraph} 
                                    onChange={i => updateManifest('knowledgeGraph', i)} 
                                    placeholder="Add domain..." 
                                />
                                <button 
                                    onClick={() => setIsSkillPickerOpen(true)}
                                    className="w-full alce-button baunk-style text-[8px] border-dashed border-agent text-agent hover:bg-agent hover:text-white flex justify-center py-3"
                                >
                                    [ + IMPORT_DOMAINS_FROM_SKILLS ]
                                </button>
                            </div>
                            
                        </div>
                    </div>

                    {/* Skill Picker Overlay */}
                    {isSkillPickerOpen && (
                        <div className="absolute inset-0 z-20 bg-white/95 backdrop-blur-md p-6 flex flex-col animate-in fade-in zoom-in-95 border border-sovereign shadow-xl">
                            <div className="flex justify-between items-center mb-6 border-b border-sovereign pb-2">
                                <h4 className="baunk-style text-[10px] tracking-widest">SELECT_COGNITIVE_MODULES_TO_INGEST</h4>
                                <button onClick={() => setIsSkillPickerOpen(false)} className="text-zinc hover:text-black font-bold">✕</button>
                            </div>
                            <div className="flex-1 overflow-y-auto grid grid-cols-1 md:grid-cols-2 gap-3 mb-6 scrollbar-hide">
                                {SKILL_DATABASE.map(skill => {
                                    const isSelected = selectedSkillsForIngest.includes(skill.id);
                                    return (
                                        <div 
                                            key={skill.id}
                                            onClick={() => {
                                                setSelectedSkillsForIngest(prev => 
                                                    isSelected ? prev.filter(id => id !== skill.id) : [...prev, skill.id]
                                                );
                                            }}
                                            className={`p-4 border cursor-pointer transition-all ${isSelected ? 'bg-agent/10 border-agent' : 'bg-zinc/5 border-zinc/10 hover:border-zinc/30'}`}
                                        >
                                            <div className="flex justify-between items-start mb-2">
                                                <span className={`baunk-style text-[9px] ${isSelected ? 'text-agent' : 'text-zinc-600'}`}>{skill.name}</span>
                                                {isSelected && <span className="text-agent font-bold">✓</span>}
                                            </div>
                                            <p className="text-[8px] font-mono opacity-50 line-clamp-2">{skill.description}</p>
                                            <div className="mt-2 flex gap-1 flex-wrap">
                                                {skill.knowledge?.slice(0, 3).map((k, i) => (
                                                    <span key={i} className="text-[6px] bg-white px-1 border border-zinc/10 opacity-60">{k}</span>
                                                ))}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                            <div className="flex justify-end gap-2">
                                <button onClick={() => setIsSkillPickerOpen(false)} className="alce-button baunk-style text-[9px] px-4">CANCEL</button>
                                <button 
                                    onClick={handleIngestSkills}
                                    disabled={selectedSkillsForIngest.length === 0}
                                    className="alce-button baunk-style text-[9px] px-6 bg-sovereign text-white hover:bg-agent disabled:opacity-50"
                                >
                                    [ INGEST_SELECTED_MODULES ({selectedSkillsForIngest.length}) ]
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            )}

        </div>
    </div>
  );
};

export default IdentityForge;
