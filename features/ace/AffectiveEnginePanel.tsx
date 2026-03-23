import React from 'react';
import { useStore } from '../../store/useStore';
import { RealtimeBarVisualizer, CircularVisualizer } from '../../components/Visualizers';
import { useLiquidGlass } from '../../hooks/useLiquidGlass';

interface AffectiveEnginePanelProps {
    audioStream: MediaStream | null;
    videoRef: React.RefObject<HTMLVideoElement | null>;
    isCameraActive: boolean;
    toggleCamera: () => void;
    bridgeManagerRef: React.RefObject<any>;
    accentColor: string;
}

const AffectiveEnginePanel: React.FC<AffectiveEnginePanelProps> = ({
    audioStream,
    videoRef,
    isCameraActive,
    toggleCamera,
    bridgeManagerRef,
    accentColor
}) => {
    const {
        biometrics,
        updateBiometrics,
        agent,
        harmonicStatus,
        isConnected,
        cloudFiles,
        setCloudFiles,
        socialEvents,
        setSocialEvents,
        enterpriseEvents,
        setEnterpriseEvents,
        mobileView
    } = useStore();

    const resonanceLG = useLiquidGlass({ variant: 'card' });
    const coherenceLG = useLiquidGlass({ variant: 'card' });
    const healthLG = useLiquidGlass({ variant: 'card' });
    const filesLG = useLiquidGlass({ variant: 'card' });

    const getFormattedTime = (iso: string) => {
        try {
            return new Date(iso).toLocaleString('en-US', {
                month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
            });
        } catch (e) { return iso; }
    };

    return (
        <aside className={`md:col-span-3 glass-card overflow-y-auto scrollbar-hide flex flex-col ${mobileView === 'vision' ? 'flex-1' : 'hidden md:flex'}`}>
            <div className="flex-none h-48 md:h-64 lg:h-48 p-4 relative border-b border-white/10">
                <div className="glass-input w-full">
                    <CircularVisualizer stream={audioStream} active={isConnected} accent={accentColor} />
                    <video ref={videoRef} autoPlay playsInline muted className={`absolute inset-0 w-full h-full object-cover grayscale opacity-0 ${isCameraActive ? 'opacity-40' : ''}`} />
                </div>
                <button onClick={toggleCamera} className="glass-btn glass-label text-[7px] mt-4 w-full">
                    {isCameraActive ? '[ CLOSE_VISION ]' : '[ OPEN_PROBE ]'}
                </button>
            </div>

            <div className="glass-input w-full">
                <h3 className="glass-label text-[8px] opacity-40 border-b border-sovereign pb-1 text-center">Affective_Engine_v4.3</h3>

                <div className="flex flex-col gap-6">
                    <div ref={resonanceLG.ref as any} style={resonanceLG.style} {...resonanceLG.handlers} className="space-y-4 p-3 border border-sovereign/5 relative overflow-hidden group">
                        <div className="absolute inset-0 pointer-events-none opacity-50 transition-opacity group-hover:opacity-100" style={{ backgroundImage: resonanceLG.glintGradient }} />
                        <span className="glass-label text-[6px] opacity-30 block mb-1">User_Resonance_Manifold</span>
                        <RealtimeBarVisualizer label="Valence (Emotion)" value={biometrics.emotional} color="#000000" onChange={(val) => updateBiometrics({ emotional: val })} />
                        <RealtimeBarVisualizer label="Arousal (Physical)" value={biometrics.physical} color="#FF7D00" onChange={(val) => updateBiometrics({ physical: val })} />
                        <RealtimeBarVisualizer label="Cognitive Load" value={biometrics.cognitive} color="#91D65F" onChange={(val) => updateBiometrics({ cognitive: val })} />
                    </div>

                    <div ref={coherenceLG.ref as any} style={coherenceLG.style} {...coherenceLG.handlers} className="space-y-4 bg-agent/5 p-3 border border-agent/10 relative overflow-hidden group">
                        <div className="absolute inset-0 pointer-events-none opacity-50 transition-opacity group-hover:opacity-100" style={{ backgroundImage: coherenceLG.glintGradient }} />
                        <span className="glass-label text-[6px] opacity-30 block mb-1">System_Coherence_Manifold</span>
                        <RealtimeBarVisualizer label="System_Coherence" value={agent.cognitive} color="#91D65F" />
                        <RealtimeBarVisualizer label="Valence_Curvature" value={agent.valenceCurvature} color="#995CC0" />
                        <RealtimeBarVisualizer label="Manifold_Integrity" value={agent.manifoldIntegrity} color="#FF7D00" />
                    </div>

                    <div ref={healthLG.ref as any} style={healthLG.style} {...healthLG.handlers} className="space-y-4 bg-flux/5 p-3 border border-flux/10 animate-in fade-in slide-in-from-bottom-2 relative overflow-hidden group">
                        <div className="absolute inset-0 pointer-events-none opacity-50 transition-opacity group-hover:opacity-100" style={{ backgroundImage: healthLG.glintGradient }} />
                        <span className="glass-label text-[6px] opacity-30 block mb-1">HealthKit_Sovereign_Monitor (iWatch)</span>
                        <div className="grid grid-cols-2 gap-2">
                            <div className="glass-input w-full">
                                <span className="text-[6px] font-mono opacity-40 uppercase">Heart_Rate</span>
                                <span className="text-[10px] font-bold glass-label">{biometrics.hr} BPM</span>
                            </div>
                            <div className="glass-input w-full">
                                <span className="text-[6px] font-mono opacity-40 uppercase">HRV_SDNN</span>
                                <span className="text-[10px] font-bold glass-label">{biometrics.hrv} MS</span>
                            </div>
                            <div className="glass-input w-full">
                                <span className="text-[6px] font-mono opacity-40 uppercase">Respiration</span>
                                <span className="text-[10px] font-bold glass-label">{biometrics.respiratoryRate.toFixed(1)} BR/M</span>
                            </div>
                            <div className="glass-input w-full">
                                <span className="text-[6px] font-mono opacity-40 uppercase">Sleep_Eff</span>
                                <span className="text-[10px] font-bold glass-label">{Math.round(biometrics.sleepEfficiency * 100)}%</span>
                            </div>
                        </div>
                    </div>

                    {/* Cloud Files Section */}
                    <div ref={filesLG.ref as any} style={filesLG.style} {...filesLG.handlers} className="space-y-4 bg-sovereign/5 p-3 border border-[rgba(255,255,255,0.18)] animate-in fade-in slide-in-from-bottom-2 relative overflow-hidden group">
                        <div className="absolute inset-0 pointer-events-none opacity-50 transition-opacity group-hover:opacity-100" style={{ backgroundImage: filesLG.glintGradient }} />
                        <div className="flex justify-between items-center mb-1">
                            <span className="glass-label text-[6px] opacity-30 block">Sovereign_Files (iCloud)</span>
                            <button
                                onClick={async () => {
                                    const files = await bridgeManagerRef.current.retrieveFromCloud('icloud', '*');
                                    setCloudFiles(files);
                                }}
                                className="text-[6px] font-mono hover:text-agent underline opacity-50"
                            >
                                [ REFRESH ]
                            </button>
                        </div>
                        <div className="space-y-1 max-h-32 overflow-y-auto pr-1 thin-scrollbar">
                            {cloudFiles.length === 0 ? (
                                <div className="text-[7px] font-mono opacity-20 py-4 text-center">NO_FILES_INDEXED</div>
                            ) : (
                                cloudFiles.map((f, i) => (
                                    <div key={i} className="glass-input w-full">
                                        <div className="flex items-center gap-2">
                                            <div className="w-1 h-1 rounded-full bg-agent opacity-40"></div>
                                            <div className="flex flex-col">
                                                <span className="text-[8px] font-bold glass-label truncate max-w-[80px]">{f.name}</span>
                                                <span className="text-[5px] font-mono opacity-40 tracking-tighter">{f.type.toUpperCase()} • {f.size}</span>
                                            </div>
                                        </div>
                                        <button className="text-[6px] glass-label opacity-0 group-hover:opacity-100 px-1 py-0.5 bg-agent text-white rounded-[1px] shadow-sm">VAULT</button>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    <div className="space-y-2 bg-flux/5 p-3 border border-flux/10 animate-in fade-in slide-in-from-bottom-2">
                        <span className="glass-label text-[6px] opacity-30 block mb-1">Harmonic_State</span>
                        <div className="flex justify-between items-center text-[7px] font-mono">
                            <span className="opacity-60">STATUS:</span>
                            <span className={`font-bold ${harmonicStatus === 'Stress_Basin' ? 'text-red-500' : harmonicStatus === 'Loop_Detected' ? 'text-tension' : 'text-agent'}`}>
                                {harmonicStatus.toUpperCase()}
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </aside>
    );
};

export default AffectiveEnginePanel;
