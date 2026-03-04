import React from 'react';
import { SkillManifest } from '../types';

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
    return (
        <div style={{ maxWidth: 960, margin: '0 auto' }}>
            <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                marginBottom: 20, paddingBottom: 12,
                borderBottom: '1px solid var(--separator)',
            }}>
                <h2 style={{ fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em' }}>Skills</h2>
                <button onClick={onCreate} className="glass-btn glass-btn--primary" style={{ fontSize: 12, padding: '6px 16px' }}>
                    + New Skill
                </button>
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

            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                gap: 12,
            }}>
                {skills.map(skill => (
                    <div
                        key={skill.id}
                        onClick={() => onSelect(skill)}
                        style={{
                            background: 'var(--glass-bg)',
                            border: `1px solid ${skill.verified ? 'var(--glass-edge)' : 'var(--separator)'}`,
                            borderRadius: 14,
                            padding: 16,
                            cursor: 'pointer',
                            transition: 'all 0.2s ease',
                            opacity: skill.verified ? 1 : 0.5,
                            filter: skill.verified ? 'none' : 'grayscale(0.6)',
                            position: 'relative',
                            overflow: 'hidden',
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.borderColor = 'rgba(48,209,88,0.30)';
                            e.currentTarget.style.boxShadow = 'var(--glass-shadow)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.borderColor = skill.verified ? 'var(--glass-edge)' : 'var(--separator)';
                            e.currentTarget.style.boxShadow = 'none';
                        }}
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
                                    style={{
                                        background: 'none', border: 'none', cursor: 'pointer',
                                        color: 'var(--accent-danger)', fontSize: 14, padding: '2px 4px',
                                        opacity: 0.4, transition: 'opacity 0.15s',
                                    }}
                                    onMouseEnter={e => e.currentTarget.style.opacity = '1'}
                                    onMouseLeave={e => e.currentTarget.style.opacity = '0.4'}
                                >✕</button>
                                <button
                                    onClick={(e) => { e.stopPropagation(); onToggle(skill.id); }}
                                    className={`glass-btn ${skill.verified ? 'glass-btn--primary' : ''}`}
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

                        {/* Capabilities */}
                        <div style={{ marginBottom: 8 }}>
                            <p style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-quaternary)', textTransform: 'uppercase', marginBottom: 4 }}>Capabilities</p>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                                {(skill.capabilities || []).length > 0 ? (
                                    skill.capabilities.slice(0, 4).map((cap, ci) => (
                                        <span key={ci} style={{
                                            padding: '2px 6px', borderRadius: 4,
                                            background: 'var(--fill-quaternary)',
                                            border: '1px solid var(--separator)',
                                            fontSize: 10, fontFamily: 'var(--font-mono)',
                                            color: 'var(--text-secondary)',
                                        }}>{cap}</span>
                                    ))
                                ) : (
                                    <span style={{ fontSize: 10, fontStyle: 'italic', color: 'var(--text-quaternary)' }}>No bindings</span>
                                )}
                                {(skill.capabilities || []).length > 4 && (
                                    <span style={{ fontSize: 10, color: 'var(--text-quaternary)' }}>+{skill.capabilities.length - 4}</span>
                                )}
                            </div>
                        </div>

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
    );
};

interface SkillDetailOverlayProps {
    skill: SkillManifest;
    onClose: () => void;
}

export const SkillDetailOverlay: React.FC<SkillDetailOverlayProps> = ({ skill, onClose }) => {
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
                    <button onClick={onClose} className="glass-btn" style={{ fontSize: 12, padding: '4px 12px' }}>Close</button>
                </div>

                {/* Content */}
                <div style={{ flex: 1, overflowY: 'auto', padding: 24, display: 'flex', flexDirection: 'column', gap: 24 }} className="scrollbar-hide">
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
