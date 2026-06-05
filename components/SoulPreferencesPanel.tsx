
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import React, { useState, useEffect, useCallback, useRef } from 'react';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { PolytopeIdentity } from './Identity';
import PersonalityField from './PersonalityField';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { SoulPreferences, SoulHumor, SoulConciseness, SoulManifest, SkillManifest } from '../types';
import { getCsrfToken } from '../csrfStore';
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import SkillBuilderWizard from './SkillBuilderWizard';
import { SKILL_DATABASE } from '../knowledge';
import { HeartbeatOrderEditor } from '../features/heartbeat/HeartbeatOrderEditor';

const DAEMON_URL = 'http://localhost:8000';

// Compact Radar Chart — SVG
const RadarChart: React.FC<{ preferences: SoulPreferences }> = ({ preferences }) => {
    const size = 140;
    const center = size / 2;
    const radius = (size / 2) - 12;

    const keys: (keyof SoulPreferences)[] = ['tone', 'assertiveness', 'empathy', 'creativity'];
    const labels = ['Tone', 'Assert', 'Empathy', 'Create'];
    const values = keys.map(k => preferences[k] as number);
    const angleSlice = (Math.PI * 2) / keys.length;

    const points = values.map((val, i) => {
        const angle = i * angleSlice - (Math.PI / 2);
        return [
            center + (radius * val * Math.cos(angle)),
            center + (radius * val * Math.sin(angle))
        ];
    });

    const polyPoints = points.map(p => p.join(',')).join(' ');

    return (
        <div style={{ position: 'relative', width: size, height: size, margin: '0 auto' }}>
            <svg width={size} height={size}>
                <circle cx={center} cy={center} r={radius} fill="none" stroke="var(--separator)" strokeWidth="1" />
                <circle cx={center} cy={center} r={radius * 0.5} fill="none" stroke="var(--separator)" strokeWidth="0.5" strokeDasharray="3 3" />
                {values.map((_, i) => {
                    const angle = i * angleSlice - (Math.PI / 2);
                    return (
                        <line key={i} x1={center} y1={center}
                            x2={center + radius * Math.cos(angle)}
                            y2={center + radius * Math.sin(angle)}
                            stroke="var(--separator)" strokeWidth="0.5" />
                    );
                })}
                <polygon points={polyPoints} fill="rgba(48, 209, 88, 0.10)" stroke="rgba(48, 209, 88, 0.45)" strokeWidth="1.5" />
                {points.map((p, i) => (
                    <circle key={i} cx={p[0]} cy={p[1]} r="3" fill="rgba(48, 209, 88, 0.55)" stroke="rgba(48, 209, 88, 0.25)" strokeWidth="1" />
                ))}
            </svg>
            {labels.map((label, i) => {
                const angle = i * angleSlice - (Math.PI / 2);
                const lx = center + (radius + 14) * Math.cos(angle);
                const ly = center + (radius + 14) * Math.sin(angle);
                return (
                    <span key={i} style={{
                        position: 'absolute',
                        left: lx, top: ly,
                        transform: 'translate(-50%, -50%)',
                        fontSize: 10,
                        fontWeight: 500,
                        color: 'var(--text-tertiary)',
                        letterSpacing: '0.02em',
                        whiteSpace: 'nowrap',
                    }}>{label}</span>
                );
            })}
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
    const add = () => { if (val.trim()) { onChange([...items, val.trim()]); setVal(''); } };
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>{label}</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {items.map((it, i) => (
                    <span key={i} style={{
                        display: 'inline-flex', alignItems: 'center', gap: 4,
                        padding: '3px 8px',
                        background: 'var(--fill-quaternary)',
                        border: '1px solid var(--separator)',
                        borderRadius: 6,
                        fontSize: 12, fontFamily: 'var(--font-mono)',
                        color: 'var(--text-primary)',
                    }}>
                        {it}
                        <button onClick={() => onChange(items.filter((_, idx) => idx !== i))}
                            style={{ background: 'none', border: 'none', color: 'var(--accent-danger)', cursor: 'pointer', fontSize: 14, lineHeight: 1, padding: 0 }}>×</button>
                    </span>
                ))}
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
                <input
                    className="glass-input"
                    value={val}
                    onChange={e => setVal(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && add()}
                    placeholder={placeholder}
                    style={{ flex: 1 }}
                />
                <button onClick={add} className="glass-btn" style={{ padding: '6px 12px', flexShrink: 0 }}>+</button>
            </div>
        </div>
    );
};

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const IdentityForge: React.FC<{ onClose: () => void; onManifestUpdate?: (manifest: SoulManifest) => void }> = ({ onClose, onManifestUpdate }) => {
    const [tab, setTab] = useState<'IDENTITY' | 'COGNITION'>('IDENTITY');
    const [manifest, setManifest] = useState<SoulManifest | null>(null);
    const [loading, setLoading] = useState(true);
    const [isDirty, setIsDirty] = useState(false);
    const [saving, setSaving] = useState(false);
    const [isSkillPickerOpen, setIsSkillPickerOpen] = useState(false);
    const [selectedSkillsForIngest, setSelectedSkillsForIngest] = useState<string[]>([]);

    const fetchManifest = async () => {
        const token = localStorage.getItem('alluci_daemon_token');
        try {
            const controller = new AbortController();
            const id = setTimeout(() => controller.abort(), 1000);
            const res = await fetch(`${DAEMON_URL}/api/v1/soul/manifest`, {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {},
                signal: controller.signal
            });
            clearTimeout(id);
            if (res.ok) { setManifest(await res.json()); setLoading(false); return; }
            throw new Error("Failed to load from Daemon");
        } catch (e) {
            console.warn("Daemon unreachable, checking local cache.");
            const cached = localStorage.getItem('alluci_soul_manifest');
            // eslint-disable-next-line no-empty
            if (cached) { try { setManifest(JSON.parse(cached)); setLoading(false); return; } catch (err) { } }
            setManifest({
                preferences: { tone: 0.5, humor: SoulHumor.DRY, empathy: 0.5, assertiveness: 0.5, creativity: 0.5, verbosity: 0.5, conciseness: SoulConciseness.BALANCED },
                identityCore: "OFFLINE_MODE: You are Alluci, a Sovereign Executive Assistant.",
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

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const updateManifest = (key: keyof SoulManifest, val: any) => {
        if (!manifest) return;
        setManifest({ ...manifest, [key]: val });
        setIsDirty(true);
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
            const csrfToken = await getCsrfToken(DAEMON_URL, token);
            const res = await fetch(`${DAEMON_URL}/api/v1/soul/manifest`, {
                method: 'PUT',
                headers: { 
                    'Content-Type': 'application/json', 
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
                    ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {})
                },
                body: JSON.stringify(manifest)
            });
            if (res.ok) { setIsDirty(false); }
            else if (res.status === 429) { alert("Biometric stress detected. Please calm down."); throw new Error("Throttled"); }
            else throw new Error("Backend Error");
        } catch (e) {
            console.warn("Daemon offline, saving locally.");
            localStorage.setItem('alluci_soul_manifest', JSON.stringify(manifest));
            setIsDirty(false);
        } finally {
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
            items.forEach(item => { if (!arr.includes(item)) arr.push(item); });
            return arr;
        };
        skillsToIngest.forEach(skill => {
            if (!newManifest.active_skill_ids) {
                newManifest.active_skill_ids = [];
            }
            if (!newManifest.active_skill_ids.includes(skill.id)) {
                newManifest.active_skill_ids.push(skill.id);
            }
        });
        setManifest(newManifest);
        setIsDirty(true);
        setIsSkillPickerOpen(false);
        setSelectedSkillsForIngest([]);
    };

    if (loading || !manifest) return (
        <div style={{ padding: 40, color: 'var(--text-tertiary)', fontSize: 13, fontFamily: 'var(--font-mono)' }}>
            Loading identity matrix...
        </div>
    );

    return (
        <div style={{ maxWidth: 920, margin: '0 auto' }}>
            {/* Header */}
            <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                paddingBottom: 14, marginBottom: 24,
                borderBottom: '1px solid var(--separator)',
            }}>
                <div style={{ display: 'flex', gap: 0, background: 'var(--fill-quaternary)', borderRadius: 8, padding: 2, border: '1px solid var(--separator)' }}>
                    {['IDENTITY', 'COGNITION'].map((t) => (
                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                        <button key={t} onClick={() => setTab(t as any)} style={{
                            padding: '6px 16px',
                            borderRadius: 6,
                            fontSize: 12, fontWeight: 500,
                            border: 'none', cursor: 'pointer',
                            background: tab === t ? 'var(--glass-bg-hover)' : 'transparent',
                            color: tab === t ? 'var(--text-primary)' : 'var(--text-tertiary)',
                            transition: 'all 0.15s ease',
                            boxShadow: tab === t ? 'var(--glass-shadow)' : 'none',
                        }}>
                            {t}
                        </button>
                    ))}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    {isDirty && <span style={{ fontSize: 11, color: 'var(--accent-warm)', fontWeight: 500 }}>Unsaved</span>}
                    <button onClick={commitChanges} disabled={saving} className="glass-btn glass-btn--primary" style={{ fontSize: 12, padding: '6px 18px' }}>
                        {saving ? 'Saving...' : 'Save Changes'}
                    </button>
                </div>
            </div>

            {/* IDENTITY TAB */}
            {tab === 'IDENTITY' && (
                <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 28 }}>
                    {/* Left: Radar + Hash */}
                    <div style={{
                        background: 'var(--fill-quaternary)',
                        border: '1px solid var(--separator)',
                        borderRadius: 14,
                        padding: '28px 20px',
                        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 20,
                    }}>
                        <RadarChart preferences={manifest.preferences} />
                        <div style={{ textAlign: 'center' }}>
                            <p style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 4 }}>Soul Signature</p>
                            <p style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-quaternary)', wordBreak: 'break-all' }}>{manifest.preferences.tone * 999123 | 0}_X9</p>
                        </div>
                    </div>

                    {/* Right: Parameters + Identity */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
                        {/* Core Parameters */}
                        <section>
                            <h3 style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.03em', marginBottom: 12, paddingBottom: 8, borderBottom: '1px solid var(--separator)' }}>
                                Core Parameters
                            </h3>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                                <PersonalityField label="Tone" type="slider" value={manifest.preferences.tone} onChange={v => updatePrefs('tone', v)} description="Casual ↔ Formal" />
                                <PersonalityField label="Empathy" type="slider" value={manifest.preferences.empathy} onChange={v => updatePrefs('empathy', v)} description="Validation weight" />
                                <PersonalityField label="Assertiveness" type="slider" value={manifest.preferences.assertiveness} onChange={v => updatePrefs('assertiveness', v)} description="Directive strength" />
                                <PersonalityField label="Creativity" type="slider" value={manifest.preferences.creativity} onChange={v => updatePrefs('creativity', v)} description="Divergence" />
                            </div>
                        </section>

                        {/* Identity */}
                        <section>
                            <h3 style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.03em', marginBottom: 12, paddingBottom: 8, borderBottom: '1px solid var(--separator)' }}>
                                Identity & Voice
                            </h3>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                                <div>
                                    <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', display: 'block', marginBottom: 4, textTransform: 'uppercase' }}>Identity Core</label>
                                    <textarea className="glass-input" value={manifest.identityCore} onChange={e => updateManifest('identityCore', e.target.value)} style={{ minHeight: 64, resize: 'vertical', fontSize: 13 }} />
                                </div>
                                <div>
                                    <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', display: 'block', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Heartbeat Pulse Configuration</label>
                                    <div className="bg-zinc-950/20 border border-zinc-800/50 rounded-2xl p-4">
                                        <HeartbeatOrderEditor 
                                            initialOrders={(() => {
                                                const raw = manifest.heartbeat;
                                                if (!raw) return [];
                                                if (typeof raw === 'string') {
                                                    // Auto-migrate legacy markdown to structured
                                                    if (raw.trim().startsWith('- [')) {
                                                        return raw.split('\n')
                                                            .filter(l => l.trim().startsWith('- [x]'))
                                                            .map(l => ({
                                                                id: Math.random().toString(36).substring(2, 9),
                                                                label: l.replace('- [x]', '').trim(),
                                                                active: true,
                                                                probe_type: 'task_deadline',
                                                                probe_config: { path: 'TASKS.md' },
                                                                action_type: 'execute_objective',
                                                                action_config: { objective_template: l.replace('- [x]', '').trim() },
                                                                interval_minutes: 15
                                                            }));
                                                    }
                                                    try { return JSON.parse(raw); } catch(e) { return []; }
                                                }
                                                return Array.isArray(raw) ? raw : [];
                                            })()}
                                            onSave={(orders) => updateManifest('heartbeat', orders)}
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', display: 'block', marginBottom: 4, textTransform: 'uppercase' }}>Voice Profile</label>
                                    <select className="glass-input" value={manifest.voiceProfile || 'am_adam'} onChange={e => updateManifest('voiceProfile', e.target.value)} style={{ fontSize: 13, width: '100%' }}>
                                        <option value="am_adam">am_adam (Masculine / Deep Work)</option>
                                        <option value="af_heart">af_heart (Feminine / Peak Performance)</option>
                                        <option value="af_bella">af_bella (Feminine / Ambient)</option>
                                        <option value="am_michael">am_michael (Masculine / Assertive)</option>
                                        <option value="af_sky">af_sky (Feminine / Calm)</option>
                                    </select>
                                </div>
                                <TagInput label="Prime Directives" items={manifest.directives} onChange={i => updateManifest('directives', i)} placeholder="Add directive..." />
                            </div>
                        </section>
                    </div>
                </div>
            )}

            {/* COGNITION TAB */}
            {tab === 'COGNITION' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 28, position: 'relative' }}>
                    {/* Left: Structural Logic */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                        <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent)', marginBottom: 4 }}>Structural Logic</h3>
                        <div>
                            <label style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-tertiary)', display: 'block', marginBottom: 4, textTransform: 'uppercase' }}>Reasoning Style</label>
                            <textarea className="glass-input" value={manifest.reasoningStyle} onChange={e => updateManifest('reasoningStyle', e.target.value)} style={{ minHeight: 56, resize: 'vertical', fontSize: 13 }} />
                        </div>
                        <TagInput label="Frameworks" items={manifest.frameworks} onChange={i => updateManifest('frameworks', i)} placeholder="Add mental model..." />
                        <TagInput label="Mindsets" items={manifest.mindsets} onChange={i => updateManifest('mindsets', i)} placeholder="Add attitude..." />
                        <TagInput label="Methodologies" items={manifest.methodologies || []} onChange={i => updateManifest('methodologies', i)} placeholder="Add template..." />
                        <TagInput label="Cognitive Chains" items={manifest.chainsOfThought || []} onChange={i => updateManifest('chainsOfThought', i)} placeholder="Add chain step..." />
                        <TagInput label="Logic Axioms" items={manifest.logic || []} onChange={i => updateManifest('logic', i)} placeholder="Add axiom..." />
                        <TagInput label="Best Practices" items={manifest.bestPractices || []} onChange={i => updateManifest('bestPractices', i)} placeholder="Add standard..." />
                    </div>

                    {/* Right: Knowledge */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                        <h3 style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent-secondary)', marginBottom: 4 }}>Knowledge Graph</h3>
                        <div style={{
                            background: 'var(--fill-quaternary)',
                            border: '1px solid var(--separator)',
                            borderRadius: 14,
                            padding: 20,
                            display: 'flex', flexDirection: 'column', gap: 14, flex: 1,
                        }}>
                            <TagInput label="Active Domains" items={manifest.knowledgeGraph} onChange={i => updateManifest('knowledgeGraph', i)} placeholder="Add domain..." />
                            <button
                                onClick={() => setIsSkillPickerOpen(true)}
                                className="glass-btn"
                                style={{
                                    width: '100%', padding: '10px',
                                    borderStyle: 'dashed',
                                    color: 'var(--accent)',
                                    fontSize: 12,
                                    textAlign: 'center',
                                }}
                            >
                                + Assign Skills to Agent
                            </button>
                        </div>
                    </div>

                    {/* Skill Picker Overlay */}
                    {isSkillPickerOpen && (
                        <div style={{
                            position: 'fixed', inset: 0, zIndex: 200,
                            background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(8px)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
                        }}>
                            <div style={{
                                background: 'var(--bg-elevated)',
                                borderRadius: 16, border: '1px solid var(--separator)',
                                maxWidth: 680, width: '100%', maxHeight: '75vh',
                                display: 'flex', flexDirection: 'column', overflow: 'hidden',
                                boxShadow: 'var(--glass-shadow-lg)',
                            }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 20px', borderBottom: '1px solid var(--separator)' }}>
                                    <h4 style={{ fontSize: 14, fontWeight: 600 }}>Select Cognitive Modules</h4>
                                    <button onClick={() => setIsSkillPickerOpen(false)} style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', fontSize: 18 }}>✕</button>
                                </div>
                                <div style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                                    {SKILL_DATABASE.map(skill => {
                                        const isSelected = selectedSkillsForIngest.includes(skill.id);
                                        return (
                                            <div key={skill.id} onClick={() => {
                                                setSelectedSkillsForIngest(prev =>
                                                    isSelected ? prev.filter(id => id !== skill.id) : [...prev, skill.id]
                                                );
                                            }} style={{
                                                padding: 12, borderRadius: 10, cursor: 'pointer',
                                                border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--separator)'}`,
                                                background: isSelected ? 'var(--accent-tint)' : 'var(--fill-quaternary)',
                                                transition: 'all 0.15s ease',
                                            }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: 4 }}>
                                                    <span style={{ fontSize: 12, fontWeight: 600, color: isSelected ? 'var(--accent)' : 'var(--text-primary)' }}>{skill.name}</span>
                                                    {isSelected && <span style={{ color: 'var(--accent)', fontWeight: 700 }}>✓</span>}
                                                </div>
                                                <p style={{ fontSize: 11, color: 'var(--text-tertiary)', lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{skill.description}</p>
                                            </div>
                                        );
                                    })}
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, padding: '12px 20px', borderTop: '1px solid var(--separator)' }}>
                                    <button onClick={() => setIsSkillPickerOpen(false)} className="glass-btn" style={{ fontSize: 12 }}>Cancel</button>
                                    <button onClick={handleIngestSkills} disabled={selectedSkillsForIngest.length === 0} className="glass-btn glass-btn--primary" style={{ fontSize: 12, opacity: selectedSkillsForIngest.length === 0 ? 0.4 : 1 }}>
                                        Assign Selected ({selectedSkillsForIngest.length})
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default IdentityForge;
