
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import React, { useState, useEffect } from 'react';
import {
    Rocket,
    User,
    Key,
    Cpu,
    ChevronRight,
    ChevronLeft,
    CheckCircle2,
    Lock,
    Zap,
    ShieldCheck,
    Brain
} from 'lucide-react';
import { useStore } from '../../store/useStore';

const SUGGESTED_SKILLS = [
    { id: 'researcher', name: 'Deep Researcher', icon: <Zap className="w-5 h-5" />, description: 'Autonomous web search and information synthesis.' },
    { id: 'coder', name: 'Sovereign Coder', icon: <Cpu className="w-5 h-5" />, description: 'Local file system access and code generation.' },
    { id: 'creative', name: 'Creative Visionary', icon: <Brain className="w-5 h-5" />, description: 'Multimodal image analysis and creative writing.' },
];

export const OnboardingWizard: React.FC = () => {
    const { setNeedsOnboarding, accessToken } = useStore();
    const [step, setStep] = useState(0);
    const [isCompleting, setIsCompleting] = useState(false);

    // Form State
    const [sovereigntyLevel, setSovereigntyLevel] = useState<1 | 2 | 3>(1);
    const [identityName, setIdentityName] = useState('');
    const [masterKey, setMasterKey] = useState('');
    const [geminiKey, setGeminiKey] = useState('');
    const [ollamaUrl, setOllamaUrl] = useState('http://127.0.0.1:11434');
    const [selectedSkill, setSelectedSkill] = useState(SUGGESTED_SKILLS[0].id);

    const nextStep = () => setStep(s => Math.min(s + 1, 4));
    const prevStep = () => setStep(s => Math.max(s - 1, 0));

    const handleFinish = async () => {
        setIsCompleting(true);
        try {
            const DAEMON_URL = (import.meta.env.VITE_DAEMON_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

            const payload = {
                identity_name: identityName,
                sovereignty_level: sovereigntyLevel,
                soul_manifest: {
                    identityCore: `You are ${identityName}, an autonomous sovereign agent.`,
                    reasoningStyle: "Direct and analytical.",
                    first_skill: selectedSkill
                },
                api_keys: {
                    llm: { googleCloud: geminiKey }
                },
                config: {
                    master_key: masterKey,
                    ollama_url: ollamaUrl
                }
            };

            const res = await fetch(`${DAEMON_URL}/api/v1/onboarding/complete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${accessToken}`
                },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                setNeedsOnboarding(false);
            } else {
                const err = await res.json();
                alert(`Error: ${err.detail || 'Failed to complete onboarding'}`);
            }
        } catch (e) {
            console.error(e);
            alert('Network error during onboarding');
        } finally {
            setIsCompleting(false);
        }
    };

    const renderStep = () => {
        switch (step) {
            case 0:
                return (
                    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <div className="flex justify-center mb-8">
                            <div className="w-20 h-20 rounded-full bg-indigo-500/20 flex items-center justify-center border border-indigo-500/30">
                                <Rocket className="w-10 h-10 text-indigo-400" />
                            </div>
                        </div>
                        <h2 className="text-3xl font-bold text-center bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
                            Welcome to the Manifold
                        </h2>
                        <p className="text-gray-400 text-center max-w-sm mx-auto">
                            Your autonomous executive node is ready for instantiation. Let's configure your sovereign presence.
                        </p>
                    </div>
                );
            case 1:
                return (
                    <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
                        <div className="flex items-center gap-3 mb-2">
                            <ShieldCheck className="w-5 h-5 text-indigo-400" />
                            <h3 className="text-xl font-semibold">Sovereignty Level</h3>
                        </div>
                        <p className="text-sm text-gray-400">Choose your deployment model. You can always increase your sovereignty level later.</p>
                        <div className="space-y-3">
                            {[
                                { level: 1 as const, name: "Level 1: Cloud-First", desc: "Zero local setup. Uses cloud LLMs and cloud storage.", icon: <Zap className="w-5 h-5" /> },
                                { level: 2 as const, name: "Level 2: Hybrid Local", desc: "Local LLM via Ollama for privacy, cloud fallback.", icon: <Cpu className="w-5 h-5" /> },
                                { level: 3 as const, name: "Level 3: Full Sovereign", desc: "Air-gapped capable. Local LLM, encrypted vault, E2E bridges.", icon: <Lock className="w-5 h-5" /> }
                            ].map(opt => (
                                <div key={opt.level} onClick={() => setSovereigntyLevel(opt.level)} className={`p-4 rounded-2xl border cursor-pointer transition-all ${sovereigntyLevel === opt.level ? 'bg-indigo-500/10 border-indigo-500/50' : 'bg-white/5 border-white/10 hover:border-white/20'}`}>
                                    <div className="flex items-center gap-3">
                                        <div className={`p-2 rounded-lg ${sovereigntyLevel === opt.level ? 'bg-indigo-500/20 text-indigo-400' : 'bg-white/10 text-gray-400'}`}>{opt.icon}</div>
                                        <div className="flex-1">
                                            <div className="font-semibold">{opt.name}</div>
                                            <div className="text-xs text-gray-500">{opt.desc}</div>
                                        </div>
                                        {sovereigntyLevel === opt.level && <CheckCircle2 className="w-5 h-5 text-indigo-400" />}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                );
            case 2:
                return (
                    <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
                        <div className="flex items-center gap-3 mb-2">
                            <User className="w-5 h-5 text-indigo-400" />
                            <h3 className="text-xl font-semibold">Identity Anchor</h3>
                        </div>
                        <p className="text-sm text-gray-400">What should we call your sovereign core? This name defines your agent's persona across all manifolds.</p>
                        <input
                            type="text"
                            placeholder="e.g. Athena, HAL, Sovereign-1"
                            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-lg outline-none focus:border-indigo-500/50 transition-colors"
                            value={identityName}
                            onChange={(e) => setIdentityName(e.target.value)}
                            autoFocus
                        />
                    </div>
                );
            case 3:
                return (
                    <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
                        <div className="flex items-center gap-3 mb-2">
                            <Key className="w-5 h-5 text-indigo-400" />
                            <h3 className="text-xl font-semibold">Authentication & Connectivity</h3>
                        </div>
                        <p className="text-sm text-gray-400">Configure keys required for Level {sovereigntyLevel} autonomy.</p>
                        <div className="space-y-4">
                            {sovereigntyLevel >= 3 && (
                                <label className="block">
                                    <span className="text-xs font-bold text-gray-500 uppercase tracking-widest ml-1 flex items-center gap-2"><Lock className="w-3 h-3" /> Master Vault Key</span>
                                    <input
                                        type="password"
                                        placeholder="Enter security phrase"
                                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 mt-1 outline-none focus:border-indigo-500/50 transition-colors"
                                        value={masterKey}
                                        onChange={(e) => setMasterKey(e.target.value)}
                                    />
                                </label>
                            )}
                            
                            {sovereigntyLevel >= 2 && (
                                <label className="block">
                                    <span className="text-xs font-bold text-gray-500 uppercase tracking-widest ml-1 flex items-center gap-2"><Cpu className="w-3 h-3" /> Ollama Endpoint</span>
                                    <input
                                        type="text"
                                        placeholder="http://127.0.0.1:11434"
                                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 mt-1 outline-none focus:border-indigo-500/50 transition-colors"
                                        value={ollamaUrl}
                                        onChange={(e) => setOllamaUrl(e.target.value)}
                                    />
                                </label>
                            )}

                            <label className="block">
                                <span className="text-xs font-bold text-gray-500 uppercase tracking-widest ml-1 flex items-center gap-2"><Zap className="w-3 h-3" /> Gemini API Key {sovereigntyLevel >= 2 ? '(Fallback)' : '(Primary)'}</span>
                                <input
                                    type="password"
                                    placeholder="AIzaSy..."
                                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 mt-1 outline-none focus:border-indigo-500/50 transition-colors"
                                    value={geminiKey}
                                    onChange={(e) => setGeminiKey(e.target.value)}
                                />
                            </label>
                        </div>
                    </div>
                );
            case 4:
                return (
                    <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
                        <div className="flex items-center gap-3 mb-2">
                            <Brain className="w-5 h-5 text-indigo-400" />
                            <h3 className="text-xl font-semibold">Initial Skillset</h3>
                        </div>
                        <p className="text-sm text-gray-400">Select a specialized module to bootstrap your agent's capabilities.</p>
                        <div className="space-y-3">
                            {SUGGESTED_SKILLS.map(skill => (
                                <div
                                    key={skill.id}
                                    onClick={() => setSelectedSkill(skill.id)}
                                    className={`p-4 rounded-2xl border cursor-pointer transition-all ${selectedSkill === skill.id
                                            ? 'bg-indigo-500/10 border-indigo-500/50 ring-1 ring-indigo-500/50'
                                            : 'bg-white/5 border-white/10 hover:border-white/20'
                                        }`}
                                >
                                    <div className="flex items-center gap-3">
                                        <div className={`p-2 rounded-lg ${selectedSkill === skill.id ? 'bg-indigo-500/20 text-indigo-400' : 'bg-white/10 text-gray-400'}`}>
                                            {skill.icon}
                                        </div>
                                        <div className="flex-1">
                                            <div className="font-semibold">{skill.name}</div>
                                            <div className="text-xs text-gray-500">{skill.description}</div>
                                        </div>
                                        {selectedSkill === skill.id && <CheckCircle2 className="w-5 h-5 text-indigo-400" />}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                );
            default:
                return null;
        }
    };

    const isNextDisabled = () => {
        if (step === 2 && !identityName) return true;
        if (step === 3) {
            if (!geminiKey) return true;
            if (sovereigntyLevel >= 3 && !masterKey) return true;
            if (sovereigntyLevel >= 2 && !ollamaUrl) return true;
        }
        return false;
    };

    return (
        <div className="fixed inset-0 z-[2000] bg-black/95 backdrop-blur-3xl flex items-center justify-center p-4">
            <div className="w-full max-w-lg bg-white/5 border border-white/10 rounded-[2.5rem] overflow-hidden shadow-2xl relative">
                {/* Progress Bar */}
                <div className="absolute top-0 left-0 right-0 h-1.5 flex gap-1 p-0.5">
                    {[0, 1, 2, 3, 4].map(s => (
                        <div
                            key={s}
                            className={`flex-1 rounded-full transition-colors duration-700 ${s <= step ? 'bg-indigo-500' : 'bg-white/10'}`}
                        />
                    ))}
                </div>

                <div className="p-10 pt-14 pb-12">
                    {renderStep()}

                    <div className="flex items-center justify-between mt-12 pt-8 border-t border-white/5">
                        <button
                            onClick={prevStep}
                            className={`flex items-center gap-2 text-sm font-semibold transition-opacity ${step === 0 ? 'opacity-0 pointer-events-none' : 'opacity-60 hover:opacity-100'}`}
                        >
                            <ChevronLeft className="w-4 h-4" /> Back
                        </button>

                        {step < 4 ? (
                            <button
                                onClick={nextStep}
                                disabled={isNextDisabled()}
                                className="bg-white text-black px-8 py-3 rounded-2xl font-bold flex items-center gap-2 hover:scale-105 active:scale-95 disabled:opacity-30 disabled:hover:scale-100 transition-all shadow-[0_0_30px_rgba(255,255,255,0.2)]"
                            >
                                {step === 0 ? "Let's Begin" : "Next Step"} <ChevronRight className="w-4 h-4" />
                            </button>
                        ) : (
                            <button
                                onClick={handleFinish}
                                disabled={isCompleting}
                                className="bg-indigo-500 text-white px-8 py-3 rounded-2xl font-bold flex items-center gap-2 hover:scale-105 active:scale-95 disabled:opacity-30 disabled:hover:scale-100 transition-all shadow-[0_0_30px_rgba(99,102,241,0.4)]"
                            >
                                {isCompleting ? (
                                    <span className="flex items-center gap-2">Instantiating... <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /></span>
                                ) : (
                                    <span className="flex items-center gap-2">Initialize Core <Lock className="w-4 h-4" /></span>
                                )}
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Background Ambience */}
            <div className="absolute inset-0 -z-10 overflow-hidden pointer-events-none">
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-500/10 rounded-full blur-[120px]" />
            </div>
        </div>
    );
};
