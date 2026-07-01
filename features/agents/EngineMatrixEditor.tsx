import React, { useState, useEffect } from 'react';
import { useStore } from '../../store/useStore';
import { Save, Server, Shield, Cpu, Image, Video, Mic, Music } from 'lucide-react';


const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

export const EngineMatrixEditor: React.FC<{
    agentId: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    engineManifest: any;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    onSave: (updatedManifest: any) => void;
}> = ({ agentId, engineManifest, onSave }) => {
    const { accessToken } = useStore();
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [providers, setProviders] = useState<any>({ llm: [], video: [], image: [], audio: [] });
    const [loading, setLoading] = useState(true);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const getInitialManifest = () => {
        if (!engineManifest) return { llm: [], video: [], image: [], audio: [], music: [] };
        if (typeof engineManifest === 'string') {
            try { return JSON.parse(engineManifest); }
            catch (e) { return { llm: [], video: [], image: [], audio: [], music: [] }; }
        }
        return engineManifest;
    };

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const [manifest, setManifest] = useState<any>(getInitialManifest());
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        setManifest(getInitialManifest());
    }, [engineManifest]);

    useEffect(() => {
        const fetchProviders = async () => {
            try {
                const res = await fetch(`${DAEMON_URL}/api/v1/system/providers`, {
                    headers: { 'Authorization': `Bearer ${accessToken}` },
                    credentials: 'include'
                });
                if (res.ok) {
                    const data = await res.json();
                    setProviders(data);
                }
            } catch (err) {
                console.error('Failed to fetch providers', err);
            } finally {
                setLoading(false);
            }
        };
        fetchProviders();
    }, [accessToken]);

    const toggleModel = (modality: string, modelId: string) => {
        const currentList = manifest[modality] || [];
        const updatedList = currentList.includes(modelId)
            ? currentList.filter((m: string) => m !== modelId)
            : [...currentList, modelId];

        setManifest({ ...manifest, [modality]: updatedList });
    };

    const handleSave = async () => {
        setSaving(true);
        await onSave(manifest);
        setSaving(false);
    };

    const modalities = [
        { id: 'llm', label: 'Language & Reasoning', icon: Cpu },
        { id: 'video', label: 'Video Synthesis', icon: Video },
        { id: 'image', label: 'Image Synthesis', icon: Image },
        { id: 'audio', label: 'Audio & Speech', icon: Mic },
        { id: 'music', label: 'Music Synthesis', icon: Music }
    ];

    if (loading) {
        return <div className="p-8 text-center text-[10px] font-mono opacity-50 tracking-widest">SCANNING_PROVIDER_MATRIX...</div>;
    }

    return (
        <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-3xl">
            <div className="bg-glass-1 border border-glass-edge p-6 rounded-2xl shadow-xl flex flex-col gap-6">
                
                <div className="flex items-center gap-3 border-b border-glass-edge pb-4">
                    <Server size={20} className="text-accent" />
                    <div>
                        <h3 className="text-sm font-medium text-text-primary">Engine Manifest Matrix</h3>
                        <p className="text-[11px] text-text-tertiary">Assign & prioritize inference capabilities for this agent manifold.</p>
                    </div>
                </div>

                <div className="flex flex-col gap-8">
                    {modalities.map((mod) => (
                        <div key={mod.id} className="flex flex-col gap-3">
                            <div className="flex items-center gap-2 border-b border-glass-pressed pb-1">
                                <mod.icon size={14} className="text-accent" />
                                <h4 className="text-[12px] font-medium tracking-wide">{mod.label}</h4>
                            </div>
                            
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                                {providers[mod.id]?.map((providerModel: any) => {
                                    const isSelected = (manifest[mod.id] || []).includes(providerModel.id);
                                    return (
                                        <div 
                                            key={providerModel.id}
                                            onClick={() => providerModel.connected && toggleModel(mod.id, providerModel.id)}
                                            className={`p-3 rounded-xl border flex items-center justify-between transition-all ${
                                                !providerModel.connected
                                                ? 'opacity-50 cursor-not-allowed bg-glass-pressed border-glass-edge/30 grayscale'
                                                : 'cursor-pointer ' + (isSelected 
                                                    ? 'bg-accent/10 border-accent/40 text-accent shadow-inner shadow-accent/5' 
                                                    : 'bg-glass-2 border-glass-edge text-text-secondary hover:border-glass-edge-hover')
                                            }`}
                                        >
                                            <div className="flex flex-col">
                                                <span className="text-[11px] font-bold">{providerModel.name}</span>
                                                <span className="text-[9px] uppercase tracking-widest opacity-60 flex items-center gap-1">
                                                    {providerModel.provider === 'local' ? <Shield size={8} /> : null}
                                                    {providerModel.provider}
                                                    {!providerModel.connected && <span className="ml-1 text-[8.5px] font-mono text-text-tertiary/80">[API DISCONNECTED]</span>}
                                                </span>
                                            </div>
                                            <div className={`relative w-7 h-4 rounded-full transition-colors ${isSelected ? 'bg-accent/80 border border-accent' : 'bg-glass-pressed border border-glass-edge'}`}>
                                                <div className={`absolute top-[1px] w-[12px] h-[12px] rounded-full transition-all duration-300 ${isSelected ? 'right-[1px] bg-white shadow-[0_0_8px_rgba(var(--accent-color),0.8)]' : 'left-[1px] bg-text-tertiary/50'}`}></div>
                                            </div>
                                        </div>
                                    );
                                })}
                                {(!providers[mod.id] || providers[mod.id].length === 0) && (
                                    <div className="p-3 rounded-xl bg-glass-pressed border border-glass-edge border-dashed text-text-tertiary text-[10px] italic flex items-center justify-center col-span-2">
                                        No providers authenticated for this modality.
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>

                <div className="flex justify-end pt-4 border-t border-glass-edge mt-2">
                    <button 
                        onClick={handleSave} 
                        disabled={saving}
                        className="glass-btn flex items-center gap-2 px-6 py-2 bg-accent/20 hover:bg-accent/30 text-accent border border-accent/40 shadow-[0_0_15px_rgba(var(--accent-color),0.15)]"
                    >
                        <Save size={14} /> {saving ? 'Writing OS...' : 'Save Engine Manifest'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default EngineMatrixEditor;
