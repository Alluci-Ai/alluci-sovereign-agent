
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import React, { useState, useEffect } from 'react';
import {
    Shield,
    Brain,
    Mic2,
    Music,
    Image as ImageIcon,
    Video,
    ArrowRight,
    ArrowLeft,
    Save,
    Plus,
    Trash2,
    Info
} from 'lucide-react';
import { ApiManifoldKeys } from '../types';
import { useStore } from '../store/useStore';
import { NetworkEgressStep } from './NetworkEgressStep';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

interface ApiWizardProps {
    isOpen: boolean;
    onClose: () => void;
    apiKeys: ApiManifoldKeys;
    onSave: (keys: ApiManifoldKeys) => void;
}

const CATEGORIES = [
    { id: 'auth', label: 'Authentication', icon: Shield, desc: 'Authenticate with your Sovereign Master Key to enable autonomous operations.' },
    { id: 'llm', label: 'LLM & Reasoning', icon: Brain, desc: 'Primary cognitive engines for text analysis and strategic planning.' },
    { id: 'audio', label: 'Audio & Voice', icon: Mic2, desc: 'Voice synthesis and real-time audio interaction.' },
    { id: 'music', label: 'Music Synthesis', icon: Music, desc: 'Sonic generation and structural composition engines.' },
    { id: 'image', label: 'Image Generation', icon: ImageIcon, desc: 'Visual synthesis and image generation.' },
    { id: 'video', label: 'Video Generation', icon: Video, desc: 'Kinetic visual synthesis and temporal coherence.' },
    { id: 'network', label: 'Network Egress', icon: Shield, desc: 'Control allowed LLM hosts and rotation schedule for outbound traffic.' },
];

const DEFAULT_PROVIDERS = {
    llm: [
        { id: 'openai', label: 'OpenAI (GPT-4o & GPT-o1)' },
        { id: 'anthropic', label: 'Anthropic (Claude 3.7)' },
        { id: 'googleCloud', label: 'Google Cloud (Gemini 2.5)' },
        { id: 'kimi', label: 'Moonshot (Kimi k2.5)' },
        { id: 'groq', label: 'Groq (LPU Inference)' },
        { id: 'deepseek', label: 'DeepSeek (R1 / Chat)' },
        { id: 'openrouter', label: 'OpenRouter' },
        { id: 'lmStudio', label: 'LM Studio (Local)' },
        { id: 'together', label: 'Together AI' },
        { id: 'cohere', label: 'Cohere (Command R+)' },
        { id: 'aws', label: 'AWS Bedrock' }
    ],
    audio: [
        { id: 'elevenLabs', label: 'ElevenLabs (Voice Synthesis)' }
    ],
    music: [
    ],
    image: [
        { id: 'midjourney', label: 'Midjourney (ImagineAPI)' }
    ],
    video: [
        { id: 'runway', label: 'RunwayML (Gen-3)' }
    ]
};

const ApiWizard: React.FC<ApiWizardProps> = ({ isOpen, onClose, apiKeys, onSave }) => {
    const [currentStep, setCurrentStep] = useState(0);
    const [egressHosts, setEgressHosts] = useState<string[]>([]);
    const [rotationSchedule, setRotationSchedule] = useState<{ interval_days: number; last_rotated: string | null }>({ interval_days: 30, last_rotated: null });
    const [localKeys, setLocalKeys] = useState<ApiManifoldKeys>(apiKeys);
    const [masterKey, setMasterKey] = useState("");
    const [isAuthenticating, setIsAuthenticating] = useState(false);
    const [authError, setAuthError] = useState("");
    const [customServiceName, setCustomServiceName] = useState("");
    const [showCustomInput, setShowCustomInput] = useState<string | null>(null);
    const { setAccessToken } = useStore();

    if (!isOpen) return null;

    const handleNext = () => {
        if (currentStep < CATEGORIES.length - 1) setCurrentStep(currentStep + 1);
        else { onSave(localKeys); onClose(); }
    };

    const handlePrev = () => { if (currentStep > 0) setCurrentStep(currentStep - 1); };

    const handleDaemonLogin = async () => {
        setIsAuthenticating(true); setAuthError("");
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/auth/login`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: masterKey }), credentials: 'include'
            });
            if (res.ok) {
                const data = await res.json();
                const token = data.access_token;
                localStorage.setItem('alluci_access_token', token);
                setAccessToken(token);
                handleNext();
            } else {
                setAuthError("Invalid key.");
            }
        } catch (e) { 
            setAuthError("Daemon unreachable."); 
        } finally { 
            setIsAuthenticating(false); 
        }
    };

    // Fetch egress config when component mounts or after auth
    useEffect(() => {
        if (isOpen) {
            (async () => {
                try {
                    const hostsRes = await fetch(`${DAEMON_URL}/api/v1/egress/hosts`, { credentials: 'include' });
                    if (hostsRes.ok) setEgressHosts((await hostsRes.json()).hosts);
                    const rotRes = await fetch(`${DAEMON_URL}/api/v1/egress/rotation`, { credentials: 'include' });
                    if (rotRes.ok) setRotationSchedule(await rotRes.json());
                } catch (e) {
                    console.error('Failed to load egress config', e);
                }
            })();
        }
    }, [isOpen]);

    const updateKey = (category: string, provider: string, val: string) => {
        setLocalKeys(prev => ({ ...prev, [category]: { ...prev[category as keyof ApiManifoldKeys], [provider]: val } }));
    };

    const addCustomService = (category: string) => {
        if (!customServiceName.trim()) return;
        updateKey(category, customServiceName.trim().toLowerCase().replace(/\s+/g, '_'), "");
        setCustomServiceName(""); setShowCustomInput(null);
    };

    const removeService = (category: string, provider: string) => {
        setLocalKeys(prev => {
            const updated = { ...prev[category as keyof ApiManifoldKeys] };
            delete updated[provider];
            return { ...prev, [category]: updated };
        });
    };

    const stepInfo = CATEGORIES[currentStep];
    const Icon = stepInfo.icon;

    return (
        <div className="glass-sheet-backdrop" onClick={onClose}>
            <div className="glass-sheet glass-sheet--open" onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div style={{
                    padding: '20px 24px',
                    borderBottom: '1px solid var(--separator)',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
                }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <div style={{
                                padding: 8, borderRadius: 10,
                                background: 'var(--fill-tertiary)',
                                color: 'var(--text-primary)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                            }}>
                                <Icon size={20} />
                            </div>
                            <h2 style={{ fontSize: 18, fontWeight: 700, letterSpacing: '-0.01em' }}>{stepInfo.label}</h2>
                        </div>
                        <p style={{ fontSize: 12, color: 'var(--text-tertiary)', maxWidth: 480 }}>{stepInfo.desc}</p>
                    </div>
                    <button onClick={onClose} style={{
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: 'var(--text-tertiary)', fontSize: 20, padding: 4,
                    }}>✕</button>
                </div>

                {/* Content */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }} className="scrollbar-hide">
                    {stepInfo.id === 'auth' ? (
                        <div style={{
                            display: 'flex', flexDirection: 'column', alignItems: 'center',
                            justifyContent: 'center', gap: 20, maxWidth: 400, margin: '0 auto', padding: '20px 0',
                        }}>
                            <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 8 }}>
                                <label style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-tertiary)' }}>Master Key</label>
                                <input
                                    type="password" value={masterKey}
                                    onChange={(e) => setMasterKey(e.target.value)}
                                    className="glass-input" placeholder="••••••••"
                                    style={{ fontSize: 14 }}
                                />
                                {authError && <p style={{ fontSize: 12, color: 'var(--accent-danger)', fontWeight: 500 }}>{authError}</p>}
                            </div>

                            <div style={{
                                padding: 14, borderRadius: 10,
                                background: 'var(--fill-quaternary)',
                                border: '1px solid var(--separator)',
                                display: 'flex', gap: 10, alignItems: 'flex-start',
                            }}>
                                <Info size={14} style={{ color: 'var(--accent)', flexShrink: 0, marginTop: 1 }} />
                                <p style={{ fontSize: 12, color: 'var(--text-tertiary)', lineHeight: 1.5 }}>
                                    API keys are stored locally in your Sovereign Manifold. They grant autonomous access to connected services.
                                </p>
                            </div>

                            <button
                                onClick={handleDaemonLogin}
                                disabled={isAuthenticating || !masterKey}
                                className="glass-btn glass-btn--primary"
                                style={{
                                    width: '100%', padding: '10px', fontSize: 14, fontWeight: 600,
                                    opacity: (isAuthenticating || !masterKey) ? 0.5 : 1,
                                }}
                            >
                                {isAuthenticating ? 'Verifying...' : 'Authenticate'}
                            </button>
                        </div>
                    ) : stepInfo.id === 'network' ? (
                        <NetworkEgressStep hosts={egressHosts} setHosts={setEgressHosts} rotation={rotationSchedule} setRotation={setRotationSchedule} />
                    ) : (
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                            gap: 10,
                        }}>
                            {[...DEFAULT_PROVIDERS[stepInfo.id as keyof typeof DEFAULT_PROVIDERS],
                            ...Object.keys(localKeys[stepInfo.id as keyof ApiManifoldKeys])
                                .filter(k => !DEFAULT_PROVIDERS[stepInfo.id as keyof typeof DEFAULT_PROVIDERS].find(p => p.id === k))
                                .map(k => ({ id: k, label: k.toUpperCase() }))
                            ].map((provider) => (
                                <div key={provider.id} style={{
                                    display: 'flex', flexDirection: 'column', gap: 6,
                                    padding: 12, borderRadius: 10,
                                    background: 'var(--fill-quaternary)',
                                    border: '1px solid var(--separator)',
                                    transition: 'border-color 0.15s ease',
                                }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <span style={{ fontSize: 12, fontWeight: 600 }}>{provider.label}</span>
                                        <button onClick={() => removeService(stepInfo.id, provider.id)} style={{
                                            background: 'none', border: 'none', cursor: 'pointer',
                                            color: 'var(--accent-danger)', opacity: 0.3, transition: 'opacity 0.15s',
                                            padding: 2,
                                        }}
                                            onMouseEnter={e => e.currentTarget.style.opacity = '1'}
                                            onMouseLeave={e => e.currentTarget.style.opacity = '0.3'}
                                        >
                                            <Trash2 size={12} />
                                        </button>
                                    </div>
                                    <input
                                        type="password"
                                        value={localKeys[stepInfo.id as keyof ApiManifoldKeys][provider.id] || ""}
                                        onChange={(e) => updateKey(stepInfo.id, provider.id, e.target.value)}
                                        placeholder="Enter token..."
                                        className="glass-input"
                                        style={{ fontSize: 12 }}
                                    />
                                </div>
                            ))}

                            {showCustomInput === stepInfo.id ? (
                                <div style={{
                                    display: 'flex', flexDirection: 'column', gap: 6,
                                    padding: 12, borderRadius: 10,
                                    border: '1px dashed var(--separator)',
                                    background: 'var(--fill-quaternary)',
                                }}>
                                    <span style={{ fontSize: 11, fontWeight: 500, color: 'var(--text-tertiary)' }}>Service Name</span>
                                    <div style={{ display: 'flex', gap: 6 }}>
                                        <input autoFocus value={customServiceName}
                                            onChange={(e) => setCustomServiceName(e.target.value)}
                                            onKeyDown={(e) => e.key === 'Enter' && addCustomService(stepInfo.id)}
                                            className="glass-input" style={{ flex: 1, fontSize: 12 }}
                                        />
                                        <button onClick={() => addCustomService(stepInfo.id)} className="glass-btn glass-btn--primary" style={{ padding: '6px', width: 36, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                            <Plus size={14} />
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <button onClick={() => setShowCustomInput(stepInfo.id)} style={{
                                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                                    padding: 14, borderRadius: 10,
                                    border: '1px dashed var(--separator)',
                                    background: 'transparent',
                                    color: 'var(--text-tertiary)',
                                    cursor: 'pointer',
                                    fontSize: 12, fontWeight: 500,
                                    transition: 'all 0.15s ease',
                                }}
                                    onMouseEnter={e => e.currentTarget.style.color = 'var(--text-primary)'}
                                    onMouseLeave={e => e.currentTarget.style.color = 'var(--text-tertiary)'}
                                >
                                    <Plus size={14} />
                                    Add Custom Service
                                </button>
                            )}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div style={{
                    padding: '14px 24px',
                    borderTop: '1px solid var(--separator)',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                    <div style={{ display: 'flex', gap: 3 }}>
                        {CATEGORIES.map((_, i) => (
                            <div key={i} style={{
                                width: i === currentStep ? 20 : 10, height: 3, borderRadius: 2,
                                background: i === currentStep ? 'var(--text-primary)' : i < currentStep ? 'var(--liquid-accent)' : 'var(--fill-tertiary)',
                                transition: 'all 0.3s ease',
                            }} />
                        ))}
                    </div>

                    <div style={{ display: 'flex', gap: 8 }}>
                        {currentStep > 0 && (
                            <button onClick={handlePrev} className="glass-btn" style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, padding: '6px 14px' }}>
                                <ArrowLeft size={13} /> Back
                            </button>
                        )}
                        {stepInfo.id !== 'auth' && (
                            <button onClick={handleNext} className="glass-btn glass-btn--primary" style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, padding: '6px 14px' }}>
                                {currentStep === CATEGORIES.length - 1 ? (
                                    <>Finalize <Save size={13} /></>
                                ) : (
                                    <>Next <ArrowRight size={13} /></>
                                )}
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ApiWizard;
