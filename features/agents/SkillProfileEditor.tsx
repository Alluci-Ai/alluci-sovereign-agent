import React, { useState, useEffect } from 'react';
import { useStore } from '../../store/useStore';
import { getCsrfToken } from '../../csrfStore';
import { ToggleLeft, ToggleRight, Settings, Save } from 'lucide-react';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

interface SkillProfileEditorProps {
    agentId: string;
}

export const SkillProfileEditor: React.FC<SkillProfileEditorProps> = ({ agentId }) => {
    const { accessToken } = useStore();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [skills, setSkills] = useState<any[]>([]);

    useEffect(() => {
        const fetchSkills = async () => {
            try {
                // 1. Try agent-specific skills endpoint (returns enabled state per-agent)
                const res = await fetch(`${DAEMON_URL}/api/v1/agents/${agentId}/skills`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include'
                });
                if (res.ok) {
                    const data = await res.json();
                    if (data.skills && data.skills.length > 0) {
                        setSkills(data.skills);
                        return;
                    }
                } else {
                    console.warn(`[SkillProfileEditor] Agent skills endpoint returned ${res.status}`);
                }

                // 2. Fallback: fetch global skills registry and mark all as dormant
                const globalRes = await fetch(`${DAEMON_URL}/api/v1/skills`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include'
                });
                if (globalRes.ok) {
                    const globalSkills = await globalRes.json();
                    const normalized = (Array.isArray(globalSkills) ? globalSkills : []).map((s: any) => ({
                        id: s.id,
                        name: s.name,
                        description: s.description || '',
                        category: s.category || 'CUSTOM',
                        enabled: false,
                        params: '{}'
                    }));
                    setSkills(normalized);
                }
            } catch (err) {
                console.error('[SkillProfileEditor] Failed fetching skills', err);
            }
        };
        fetchSkills();
    }, [agentId, accessToken]);

    const saveSkills = async (skillsState: any[]) => {
        try {
            const csrfToken = await getCsrfToken(DAEMON_URL, accessToken);
            await fetch(`${DAEMON_URL}/api/v1/agents/${agentId}/skills`, {
                method: 'PUT',
                headers: { 
                    'Authorization': `Bearer ${accessToken}`, 
                    'Content-Type': 'application/json',
                    ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {})
                },
                body: JSON.stringify({ skills: skillsState }),
                credentials: 'include'
            });
        } catch (e) {
            console.error('Failed saving skills', e);
        }
    };

    const toggleSkill = async (index: number) => {
        const next = [...skills];
        next[index].enabled = !next[index].enabled;
        setSkills(next);
        await saveSkills(next);
    };

    // Group skills by category
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const grouped: Record<string, any[]> = skills.reduce((acc: Record<string, any[]>, s: any) => {
        const cat = s.category || 'CUSTOM';
        if (!acc[cat]) acc[cat] = [];
        acc[cat].push(s);
        return acc;
    }, {});

    return (
        <div className="bg-glass-1 border border-glass-edge rounded-xl p-4 flex flex-col gap-6 animate-in fade-in zoom-in-95 duration-300 relative z-20">
            <h3 className="glass-label text-[10px] tracking-widest m-0 px-2 uppercase border-b border-glass-edge pb-2">Enabled Cognitive Skills</h3>

            {skills.length === 0 && (
                <div className="text-[12px] text-text-tertiary p-2">No skills discovered in the global registry.</div>
            )}

            {Object.entries(grouped).map(([category, catSkills]) => (
                <div key={category} className="flex flex-col gap-3 max-w-3xl">
                    <h4 className="glass-label text-[10px] tracking-widest opacity-60 m-0 uppercase flex items-center gap-2 border-b border-glass-edge/40 pb-1">
                        {category} <span className="glass-tag tracking-normal text-[9px] bg-glass-1 shadow-none">{catSkills.length}</span>
                    </h4>

                    {catSkills.map((s) => {
                        const idx = skills.indexOf(s);
                        return (
                        <div key={s.id} className={`p-4 rounded-xl border transition-colors ${s.enabled ? 'border-status-good/30 bg-status-good/5' : 'border-glass-edge bg-glass-2'}`}>
                            <div className="flex items-center justify-between cursor-pointer" onClick={() => toggleSkill(idx)}>
                                <div>
                                    <div className="flex items-center gap-2">
                                        <span className="font-semibold text-[13px] text-text-primary tracking-tight">{s.name}</span>
                                        <span className="glass-tag text-[8px] tracking-wider opacity-50">{s.category}</span>
                                    </div>
                                    <p className="text-[10px] text-text-tertiary mt-1 font-mono">{s.id}</p>
                                    <p className="text-[11px] text-text-secondary mt-1">{s.description}</p>
                                </div>
                                <div className="text-text-primary flex items-center gap-2 flex-shrink-0 ml-4">
                                    <span className={`glass-label text-[9px] ${s.enabled ? 'text-status-good' : 'opacity-40'}`}>{s.enabled ? 'ACTIVE' : 'DORMANT'}</span>
                                    {s.enabled ? <ToggleRight size={20} className="text-status-good drop-shadow-[0_0_8px_rgba(48,209,88,0.4)]" /> : <ToggleLeft size={20} className="text-glass-edge" />}
                                </div>
                            </div>

                            {s.enabled && (
                                <div className="mt-4 pt-3 border-t border-glass-edge/40 flex flex-col gap-2">
                                    <div className="flex items-center justify-between">
                                        <label className="text-[9px] font-mono uppercase text-accent flex gap-1 items-center"><Settings size={10} /> Parameter Overrides (JSON)</label>
                                        <button onClick={(e) => { e.stopPropagation(); saveSkills(skills); }} className="glass-btn gap-1" style={{ padding: '2px 8px', fontSize: 9 }}>
                                            <Save size={10} /> Save Config
                                        </button>
                                    </div>
                                    <textarea
                                        className="bg-black/40 border border-white/5 p-2 rounded-lg text-[10px] text-blue-200 font-mono resize-none outline-none h-12 overflow-hidden focus:border-accent/40 block"
                                        value={s.params || '{}'}
                                        onChange={(e) => {
                                            const next = [...skills];
                                            next[idx].params = e.target.value;
                                            setSkills(next);
                                        }}
                                        spellCheck="false"
                                        onClick={e => e.stopPropagation()}
                                    />
                                </div>
                            )}
                        </div>
                        );
                    })}
                </div>
            ))}
        </div>
    );
};

export default SkillProfileEditor;
