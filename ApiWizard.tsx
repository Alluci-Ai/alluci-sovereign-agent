
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
import { ApiManifoldKeys } from './types';

// [ CONFIGURATION_NODE ]
const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

interface ApiWizardProps {
    isOpen: boolean;
    onClose: () => void;
    apiKeys: ApiManifoldKeys;
    onSave: (keys: ApiManifoldKeys) => void;
}

const CATEGORIES = [
    { id: 'auth', label: '0. DAEMON_ACCESS_CONTROL', icon: Shield, desc: 'Authenticate with your Sovereign Master Key to enable autonomous objective execution.' },
    { id: 'llm', label: '1. LLM_REASONING_&_LOGIC', icon: Brain, desc: 'Primary cognitive engines for text analysis and strategic planning.' },
    { id: 'audio', label: '2. CONVERSATIONAL_AUDIO', icon: Mic2, desc: 'Voice synthesis and real-time audio interaction manifolds.' },
    { id: 'music', label: '3. MUSIC_SYNTHESIS', icon: Music, desc: 'Temporal sonic generation and structural composition.' },
    { id: 'image', label: '4. IMAGE_MANIFESTATION', icon: ImageIcon, desc: 'Latent space visualization and static asset genesis.' },
    { id: 'video', label: '5. VIDEO_TEMPORAL_GENESIS', icon: Video, desc: 'Kinetic visual synthesis and temporal coherence.' }
];

const DEFAULT_PROVIDERS = {
    llm: [
        { id: 'openai', label: 'OpenAI (GPT-5.1 / o1)' },
        { id: 'anthropic', label: 'Anthropic (Claude 4.5 / 4.6)' },
        { id: 'googleCloud', label: 'Google Cloud (Gemini 3)' },
        { id: 'groq', label: 'Groq (High-Speed)' },
        { id: 'deepseek', label: 'DeepSeek (R1 / V3)' }
    ],
    audio: [
        { id: 'openaiRealtime', label: 'OpenAI Realtime API' },
        { id: 'elevenLabsAgents', label: 'ElevenLabs (Agents API)' },
        { id: 'retellAi', label: 'Retell AI (Telephony)' },
        { id: 'inworldAi', label: 'Inworld AI (Character)' }
    ],
    music: [
        { id: 'suno', label: 'Suno API (Vocals/Melody)' },
        { id: 'elevenLabsMusic', label: 'ElevenLabs Music API' },
        { id: 'stableAudio', label: 'Stable Audio (Stability AI)' },
        { id: 'soundverse', label: 'Soundverse (functional)' },
        { id: 'udio', label: 'Udio (High Fidelity)' },
        { id: 'googleLyria', label: 'Google (Lyria 3)' }
    ],
    image: [
        { id: 'openaiDalle', label: 'OpenAI (DALL·E 3)' },
        { id: 'falAi', label: 'Fal.ai (Fast Diffusion)' },
        { id: 'midjourney', label: 'Midjourney (Alpha API)' },
        { id: 'adobeFirefly', label: 'Adobe Firefly API' },
        { id: 'googleNanoBanana', label: 'Google (Nano Banana)' },
        { id: 'seedance', label: 'Seedance 2.0' }
    ],
    video: [
        { id: 'runway', label: 'Runway (Gen-4.5)' },
        { id: 'luma', label: 'Luma Dream Machine' },
        { id: 'heygen', label: 'HeyGen / Synthesia' },
        { id: 'livepeer', label: 'Livepeer (Decentralized)' },
        { id: 'googleVeo', label: 'Google (Veo)' },
        { id: 'googleGenie', label: 'Google (Genie)' }
    ]
};

const ApiWizard: React.FC<ApiWizardProps> = ({ isOpen, onClose, apiKeys, onSave }) => {
    const [currentStep, setCurrentStep] = useState(0);
    const [localKeys, setLocalKeys] = useState<ApiManifoldKeys>(apiKeys);
    const [masterKey, setMasterKey] = useState("");
    const [isAuthenticating, setIsAuthenticating] = useState(false);
    const [authError, setAuthError] = useState("");
    const [customServiceName, setCustomServiceName] = useState("");
    const [showCustomInput, setShowCustomInput] = useState<string | null>(null);

    if (!isOpen) return null;

    const handleNext = () => {
        if (currentStep < CATEGORIES.length - 1) {
            setCurrentStep(currentStep + 1);
        } else {
            onSave(localKeys);
            onClose();
        }
    };

    const handlePrev = () => {
        if (currentStep > 0) {
            setCurrentStep(currentStep - 1);
        }
    };

    const handleDaemonLogin = async () => {
        setIsAuthenticating(true);
        setAuthError("");
        try {
            const res = await fetch(`${DAEMON_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: masterKey })
            });
            if (res.ok) {
                const data = await res.json();
                localStorage.setItem('alluci_daemon_token', data.access_token);
                handleNext();
            } else {
                setAuthError("FAILURE: Invalid Key.");
            }
        } catch (e) {
            setAuthError("ERROR: Daemon Unreachable.");
        } finally {
            setIsAuthenticating(false);
        }
    };

    const updateKey = (category: string, provider: string, val: string) => {
        setLocalKeys(prev => ({
            ...prev,
            [category]: {
                ...prev[category as keyof ApiManifoldKeys],
                [provider]: val
            }
        }));
    };

    const addCustomService = (category: string) => {
        if (!customServiceName.trim()) return;
        updateKey(category, customServiceName.trim().toLowerCase().replace(/\s+/g, '_'), "");
        setCustomServiceName("");
        setShowCustomInput(null);
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
        <div className="fixed inset-0 z-[400] bg-white flex flex-col simplicial-grid animate-in fade-in duration-300">
            <div className="facet flex-1 flex flex-col max-w-4xl mx-auto w-full border-t-0 shadow-2xl">
                {/* Header */}
                <div className="p-8 border-b border-black flex justify-between items-start">
                    <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-black text-white rounded-sm">
                                <Icon size={24} />
                            </div>
                            <h2 className="baunk-style text-2xl tracking-[0.2em]">{stepInfo.label}</h2>
                        </div>
                        <p className="text-[10px] font-mono opacity-60 mt-2 max-w-xl">{stepInfo.desc}</p>
                    </div>
                    <button onClick={onClose} className="text-2xl hover:bg-zinc/5 p-2 transition-colors">✕</button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-8 scrollbar-hide">
                    {stepInfo.id === 'auth' ? (
                        <div className="flex flex-col items-center justify-center h-full gap-8 max-w-md mx-auto">
                            <div className="w-full space-y-4">
                                <label className="text-[9px] baunk-style opacity-40">ENTER_SOVEREIGN_MASTER_KEY...</label>
                                <input
                                    type="password"
                                    value={masterKey}
                                    onChange={(e) => setMasterKey(e.target.value)}
                                    className="w-full bg-white border-2 border-black p-4 baunk-style text-sm tracking-widest outline-none focus:skew-x-[-1deg] transition-transform"
                                    placeholder="********"
                                />
                                {authError && <div className="text-tension text-[10px] baunk-style text-center animate-pulse">{authError}</div>}
                            </div>

                            <div className="bg-zinc/5 p-6 border border-zinc/10 rounded-sm">
                                <div className="flex gap-4 items-start">
                                    <Info size={16} className="text-agent shrink-0 mt-0.5" />
                                    <p className="text-[9px] font-mono leading-relaxed opacity-60">
                                        Security Protocol Awareness: All API keys entered here are stored within your local Sovereign Manifold (localStorage).
                                        They grant Alluci autonomous reach into your subscription silos. Ensure your environment is secure.
                                    </p>
                                </div>
                            </div>

                            <button
                                onClick={handleDaemonLogin}
                                disabled={isAuthenticating || !masterKey}
                                className={`w-full p-4 baunk-style text-[12px] flex items-center justify-center gap-3 transition-all ${isAuthenticating ? 'bg-zinc text-white animate-pulse' : 'bg-black text-white hover:bg-agent transform hover:skew-x-[-2deg]'}`}
                            >
                                {isAuthenticating ? '[ VERIFYING... ]' : '[ AUTHENTICATE ]'}
                            </button>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {[...DEFAULT_PROVIDERS[stepInfo.id as keyof typeof DEFAULT_PROVIDERS],
                            ...Object.keys(localKeys[stepInfo.id as keyof ApiManifoldKeys])
                                .filter(k => !DEFAULT_PROVIDERS[stepInfo.id as keyof typeof DEFAULT_PROVIDERS].find(p => p.id === k))
                                .map(k => ({ id: k, label: k.toUpperCase() }))
                            ].map((provider) => (
                                <div key={provider.id} className="flex flex-col gap-2 p-4 border border-zinc/10 bg-zinc/5 hover:border-black transition-colors group relative">
                                    <div className="flex justify-between items-center">
                                        <span className="text-[9px] baunk-style">{provider.label}</span>
                                        <button
                                            onClick={() => removeService(stepInfo.id, provider.id)}
                                            className="opacity-0 group-hover:opacity-40 hover:!opacity-100 text-tension p-1 transition-opacity"
                                        >
                                            <Trash2 size={12} />
                                        </button>
                                    </div>
                                    <input
                                        type="password"
                                        value={localKeys[stepInfo.id as keyof ApiManifoldKeys][provider.id] || ""}
                                        onChange={(e) => updateKey(stepInfo.id, provider.id, e.target.value)}
                                        placeholder="ENTER_TOKEN..."
                                        className="w-full bg-white border border-zinc/20 p-2 text-[10px] font-mono outline-none focus:border-black transition-colors"
                                    />
                                </div>
                            ))}

                            {showCustomInput === stepInfo.id ? (
                                <div className="flex flex-col gap-2 p-4 border-2 border-dashed border-zinc/20">
                                    <span className="text-[9px] baunk-style opacity-40">SERVICE_NAME</span>
                                    <div className="flex gap-2">
                                        <input
                                            autoFocus
                                            value={customServiceName}
                                            onChange={(e) => setCustomServiceName(e.target.value)}
                                            onKeyDown={(e) => e.key === 'Enter' && addCustomService(stepInfo.id)}
                                            className="flex-1 bg-white border border-black p-2 text-[10px] font-mono outline-none"
                                        />
                                        <button onClick={() => addCustomService(stepInfo.id)} className="bg-black text-white aspect-square w-10 flex items-center justify-center hover:bg-agent">
                                            <Plus size={16} />
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <button
                                    onClick={() => setShowCustomInput(stepInfo.id)}
                                    className="flex flex-col items-center justify-center gap-2 p-4 border-2 border-dashed border-zinc/20 hover:border-black hover:bg-zinc/5 transition-all text-zinc hover:text-black opacity-60 hover:opacity-100"
                                >
                                    <Plus size={20} />
                                    <span className="text-[10px] baunk-style">+ ADD_CUSTOM_SERVICE</span>
                                </button>
                            )}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-8 border-t border-black flex justify-between items-center bg-zinc/5">
                    <div className="flex gap-2">
                        {CATEGORIES.map((_, i) => (
                            <div
                                key={i}
                                className={`w-8 h-1 transition-all duration-500 ${i === currentStep ? 'bg-black w-12' : i < currentStep ? 'bg-agent' : 'bg-zinc/20'}`}
                            />
                        ))}
                    </div>

                    <div className="flex gap-4">
                        {currentStep > 0 && (
                            <button
                                onClick={handlePrev}
                                className="flex items-center gap-2 px-6 py-3 border border-black baunk-style text-[10px] hover:bg-zinc/5 transition-all"
                            >
                                <ArrowLeft size={14} /> [ BACK ]
                            </button>
                        )}

                        {stepInfo.id !== 'auth' && (
                            <button
                                onClick={handleNext}
                                className="flex items-center gap-2 px-8 py-3 bg-black text-white baunk-style text-[10px] hover:bg-agent transform hover:skew-x-[-2deg] transition-all"
                            >
                                {currentStep === CATEGORIES.length - 1 ? (
                                    <> [ FINALIZE_SOVEREIGN_VAULT ] <Save size={14} /> </>
                                ) : (
                                    <> [ NEXT_MODULE ] <ArrowRight size={14} /> </>
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
