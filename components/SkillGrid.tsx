import React, { useState } from 'react';
import { SkillManifest } from '../types';
import SkillFilterBar from '../features/skills/SkillFilterBar';
import SkillGrouping from '../features/skills/SkillGrouping';
import OneClickInstall from '../features/skills/OneClickInstall';
import SkillStatusPanel from '../features/skills/SkillStatusPanel';
import PerSkillKeyInput from '../features/skills/PerSkillKeyInput';

interface SkillGridProps {
    skills: SkillManifest[];
    onSelect: (skill: SkillManifest) => void;
    onToggle: (id: string) => void;
    onDelete: (id: string) => void;
    onCreate: () => void;
}

export const SkillGrid: React.FC<SkillGridProps> = ({
    skills,
    onSelect,
    onToggle,
    onDelete,
    onCreate
}) => {
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');

    // Filter pipeline natively evaluated synchronously avoiding loops
    const checkStatus = (skill: SkillManifest) => {
        if (statusFilter === 'all') return true;
        if (statusFilter === 'active') return skill.verified;
        if (statusFilter === 'error') return !skill.verified; // Simplification map
        return true;
    };

    const displaySkills = skills.filter(s => {
        const matchesSearch = s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            s.category.toLowerCase().includes(searchQuery.toLowerCase());
        return matchesSearch && checkStatus(s);
    });

    const groupedSkills = SkillGrouping(displaySkills);
    return (
        <div style={{ maxWidth: 960, margin: '0 auto' }}>
            <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                marginBottom: 20, paddingBottom: 12,
                borderBottom: '1px solid var(--separator)',
            }}>
                <div className="flex flex-col gap-2">
                    <h2 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em', margin: 0 }}>Cognitive Architectures</h2>
                    <span className="text-[10px] uppercase font-mono tracking-widest text-text-tertiary">Skill Matrix Dashboard</span>
                </div>

                <div className="flex items-center gap-4">
                    <OneClickInstall />
                    <button onClick={onCreate} className="glass-btn glass-btn--primary" style={{ fontSize: 12, padding: '8px 16px', height: '100%' }}>
                        + Build Native Skill
                    </button>
                </div>
            </div>

            <div className="mb-6 relative z-10 w-full animate-in fade-in zoom-in-95 duration-200">
                <SkillFilterBar
                    searchQuery={searchQuery}
                    setSearchQuery={setSearchQuery}
                    statusFilter={statusFilter}
                    setStatusFilter={setStatusFilter}
                />
            </div>

            {skills.length === 0 && (
                <div style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                    padding: '56px 20px', textAlign: 'center', color: 'var(--text-tertiary)',
                }}>
                    <p style={{ fontSize: 15, marginBottom: 8 }}>No skills loaded</p>
                    <p style={{ fontSize: 13 }}>Create a new cognitive module to get started.</p>
                </div>
            )}

            <div className="flex flex-col gap-8">
                {Object.keys(groupedSkills).length === 0 && skills.length > 0 && (
                    <div className="text-center py-12 text-[11px] font-mono text-text-tertiary">
                        NO_MATCHING_SIGNATURES_FOUND
                    </div>
                )}

                {Object.entries(groupedSkills as Record<string, SkillManifest[]>).map(([groupSource, groupArray]) => (
                    <div key={groupSource} className="flex flex-col gap-4">
                        <h3 className="glass-label text-[10px] tracking-widest opacity-60 m-0 uppercase flex items-center gap-2 border-b border-glass-edge pb-2">
                            {groupSource} MATRIX <span className="glass-tag tracking-normal text-[9px] bg-glass-1 shadow-none">{groupArray.length}</span>
                        </h3>

                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                            gap: 12,
                        }}>
                            {groupArray.map(skill => (
                                <div
                                    key={skill.id}
                                    onClick={() => onSelect(skill)}
                                    style={{
                                        background: 'var(--glass-bg)',
                                        border: `1px solid ${skill.verified ? 'rgba(48,209,88,0.20)' : 'var(--separator)'}`,
                                        borderRadius: 14,
                                        padding: 16,
                                        cursor: 'pointer',
                                        transition: 'all 0.2s ease',
                                        opacity: skill.verified ? 1 : 0.5,
                                        filter: skill.verified ? 'none' : 'grayscale(0.6)',
                                        position: 'relative',
                                        overflow: 'hidden',
                                    }}
                                    className="hover:shadow-[0_0_20px_rgba(48,209,88,0.05)] hover:border-[rgba(48,209,88,0.3)] transition-all group"
                                >
                                    {/* Header */}
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
                                        <div>
                                            <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>{skill.name}</p>
                                            <p style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-quaternary)', textTransform: 'uppercase' }}>{skill.category} · {skill.id}</p>
                                        </div>
                                        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); onDelete(skill.id); }}
                                                className="opacity-0 group-hover:opacity-100 transition-opacity bg-transparent border-none text-status-error text-sm p-1 hover:bg-status-error/10 rounded"
                                            >✕</button>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); onToggle(skill.id); }}
                                                className={`glass-btn ${skill.verified ? 'glass-btn--primary bg-status-good/10 text-status-good border-status-good/30' : ''}`}
                                                style={{ fontSize: 10, padding: '2px 8px', fontWeight: 500 }}
                                            >
                                                {skill.verified ? 'Active' : 'Off'}
                                            </button>
                                        </div>
                                    </div>

                                    {/* Description */}
                                    {skill.description && (
                                        <p style={{
                                            fontSize: 12, color: 'var(--text-tertiary)', lineHeight: 1.4,
                                            marginBottom: 10,
                                            display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                                        }}>{skill.description}</p>
                                    )}

                                    {/* Footer */}
                                    <div style={{
                                        paddingTop: 8, borderTop: '1px solid var(--separator)',
                                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                    }}>
                                        <span style={{ fontSize: 9, fontFamily: 'var(--font-mono)', color: 'var(--text-quaternary)' }}>SIG: {skill.signature}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

interface SkillDetailOverlayProps {
    skill: SkillManifest;
    onClose: () => void;
    onEdit?: (skill: SkillManifest) => void;
}

export const SkillDetailOverlay: React.FC<SkillDetailOverlayProps> = ({ skill, onClose, onEdit }) => {
    return (
        <div style={{
            position: 'fixed', inset: 0, zIndex: 500,
            background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(8px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
        }} onClick={onClose}>
            <div style={{
                background: 'var(--bg-elevated)',
                borderRadius: 20, border: '1px solid var(--separator)',
                maxWidth: 720, width: '100%', maxHeight: '80vh',
                display: 'flex', flexDirection: 'column', overflow: 'hidden',
                boxShadow: 'var(--glass-shadow-lg)',
            }} onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
                    padding: '20px 24px', borderBottom: '1px solid var(--separator)',
                }}>
                    <div>
                        <p style={{ fontSize: 11, fontWeight: 500, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 4 }}>{skill.category}</p>
                        <h3 style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.01em' }}>{skill.name}</h3>
                    </div>
                    <div style={{ display: 'flex', gap: 8 }}>
                        <button onClick={() => onEdit && onEdit(skill)} className="glass-btn glass-btn--primary" style={{ fontSize: 12, padding: '4px 12px' }}>Edit Module</button>
                        <button onClick={onClose} className="glass-btn" style={{ fontSize: 12, padding: '4px 12px' }}>Close</button>
                    </div>
                </div>

                {/* Content */}
                <div style={{ flex: 1, overflowY: 'auto', padding: 24, display: 'flex', flexDirection: 'column', gap: 24 }} className="scrollbar-hide">

                    <SkillStatusPanel skillId={skill.id} />

                    <section>
                        <h4 style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', marginBottom: 8 }}>Overview</h4>
                        <p style={{ fontSize: 14, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{skill.description}</p>
                    </section>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                        <section>
                            <h4 style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent)', marginBottom: 8 }}>Mindsets</h4>
                            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 6 }}>
                                {skill.mindsets.map((m, i) => (
                                    <li key={i} style={{ fontSize: 13, fontFamily: 'var(--font-mono)', display: 'flex', gap: 6 }}>
                                        <span style={{ color: 'var(--text-quaternary)' }}>{i + 1}.</span>
                                        <span>{m}</span>
                                    </li>
                                ))}
                            </ul>
                        </section>
                        <section>
                            <h4 style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-secondary)', marginBottom: 8 }}>Methodologies</h4>
                            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 6 }}>
                                {skill.methodologies.map((m, i) => (
                                    <li key={i} style={{ fontSize: 13, fontFamily: 'var(--font-mono)', display: 'flex', gap: 6 }}>
                                        <span style={{ color: 'var(--text-quaternary)' }}>{i + 1}.</span>
                                        <span>{m}</span>
                                    </li>
                                ))}
                            </ul>
                        </section>
                    </div>

                    <section>
                        <h4 style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent-warm)', marginBottom: 8 }}>Cognitive Chains & Logic</h4>
                        <div style={{
                            padding: 14, borderRadius: 10,
                            background: 'var(--fill-quaternary)',
                            border: '1px solid var(--separator)',
                            display: 'flex', flexDirection: 'column', gap: 10,
                        }}>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
                                {skill.chainsOfThought.map((t, i) => (
                                    <React.Fragment key={i}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontFamily: 'var(--font-mono)' }}>
                                            <span style={{
                                                background: 'var(--liquid-secondary)', color: 'var(--accent-secondary)',
                                                border: '0.5px solid var(--liquid-secondary-edge)',
                                                width: 18, height: 18, borderRadius: '50%',
                                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                fontSize: 9, fontWeight: 600, flexShrink: 0,
                                                backdropFilter: 'blur(8px)',
                                            }}>{i + 1}</span>
                                            <span>{t}</span>
                                        </div>
                                        {i < skill.chainsOfThought.length - 1 && <span style={{ color: 'var(--accent)', opacity: 0.4 }}>→</span>}
                                    </React.Fragment>
                                ))}
                            </div>
                            <div style={{ paddingTop: 8, borderTop: '1px solid var(--separator)' }}>
                                <p style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-quaternary)', textTransform: 'uppercase', marginBottom: 4 }}>Logic</p>
                                {skill.logic.map((l, i) => (
                                    <p key={i} style={{ fontSize: 12, fontFamily: 'var(--font-mono)', fontStyle: 'italic', color: 'var(--text-tertiary)' }}>"{l}"</p>
                                ))}
                            </div>
                        </div>
                    </section>

                    <section>
                        <h4 style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>Best Practices</h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            {skill.bestPractices && skill.bestPractices.map((b, i) => (
                                <div key={i} style={{ display: 'flex', gap: 6, fontSize: 13, fontFamily: 'var(--font-mono)', alignItems: 'flex-start' }}>
                                    <span style={{ color: 'var(--accent)' }}>●</span>
                                    <span>{b}</span>
                                </div>
                            ))}
                        </div>
                    </section>

                    <section>
                        <h4 style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent)', marginBottom: 8 }}>Tools (Extrinsic Dependencies)</h4>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            {skill.tools && skill.tools.length > 0 ? skill.tools.map((t, i) => (
                                <div key={i} style={{ display: 'flex', gap: 6, fontSize: 13, fontFamily: 'var(--font-mono)', alignItems: 'flex-start' }}>
                                    <span style={{ color: 'var(--status-good)' }}>🛠</span>
                                    <span>{t}</span>
                                </div>
                            )) : (
                                <p style={{ fontSize: 13, fontFamily: 'var(--font-mono)', color: 'var(--text-quaternary)' }}>No intrinsic tools linked.</p>
                            )}
                        </div>
                    </section>

                    <section className="bg-glass-2 border border-glass-edge p-5 rounded-xl flex flex-col gap-3">
                        <h4 className="glass-label text-[10px] tracking-widest text-text-tertiary m-0 border-b border-white/5 pb-2">Sensitive Vault Overrides</h4>
                        <PerSkillKeyInput
                            skillId={skill.id}
                            keyName="API_KEY"
                            description="Bind external 3rd party execution routing API bearer keys explicitly overriding standard system logic mapped."
                        />
                    </section>

                    <footer style={{
                        paddingTop: 14, borderTop: '1px solid var(--separator)',
                        display: 'flex', flexDirection: 'column', gap: 3,
                        fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-quaternary)',
                    }}>
                        <span>Signature: {skill.signature}</span>
                        <span>Public Key: {skill.publicKey}</span>
                    </footer>
                </div>
            </div>
        </div>
    );
};
