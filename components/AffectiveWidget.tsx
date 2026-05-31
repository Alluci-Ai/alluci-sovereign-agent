import React from 'react';
import { useStore } from '../store/useStore';
import { RealtimeBarVisualizer, CircularVisualizer } from './Visualizers';
import { ChevronDown, ChevronRight, Activity } from 'lucide-react';

interface AffectiveWidgetProps {
    audioStream: MediaStream | null;
    videoRef: React.RefObject<HTMLVideoElement | null>;
    isCameraActive: boolean;
    toggleCamera: () => void;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    bridgeManagerRef: React.RefObject<any>;
    accentColor: string;
}

const AffectiveWidget: React.FC<AffectiveWidgetProps> = ({
    audioStream,
    videoRef,
    isCameraActive,
    toggleCamera,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    bridgeManagerRef,
    accentColor,
}) => {
    const {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        biometrics, updateBiometrics,
        agent, harmonicStatus, isConnected,
        isAceExpanded, setAceExpanded,
    } = useStore();

    return (
        <div className="ace-widget">
            {/* Disclosure header */}
            <button
                onClick={() => setAceExpanded(!isAceExpanded)}
                className="ace-widget__header"
            >
                <div className="ace-widget__header-left">
                    {isAceExpanded ?
                        <ChevronDown size={14} className="ace-widget__chevron" /> :
                        <ChevronRight size={14} className="ace-widget__chevron" />
                    }
                    <Activity size={14} className="ace-widget__icon" />
                    <span className="ace-widget__title">Affective Engine</span>
                </div>
                {/* Pulse dot to show status when collapsed */}
                {!isAceExpanded && (
                    <span className={`ace-widget__pulse ${isConnected ? 'ace-widget__pulse--active' : ''}`} />
                )}
            </button>

            {/* Expandable content */}
            {isAceExpanded && (
                <div className="ace-widget__body">
                    {/* Visualizer */}
                    <div className="ace-widget__visualizer">
                        <CircularVisualizer stream={audioStream} active={isConnected} accent={accentColor} />
                        <video ref={videoRef} autoPlay playsInline muted className={`ace-widget__video ${isCameraActive ? 'ace-widget__video--active' : ''}`} />
                    </div>

                    <button onClick={toggleCamera} className="ace-widget__camera-btn">
                        {isCameraActive ? 'Close Vision' : 'Open Probe'}
                    </button>

                    {/* User resonance */}
                    <div className="ace-widget__section">
                        <span className="ace-widget__section-label">User Resonance</span>
                        <RealtimeBarVisualizer label="Valence" value={biometrics.emotional} color="#0A84FF" />
                        <RealtimeBarVisualizer label="Arousal" value={biometrics.physical} color="#FF9F0A" />
                        <RealtimeBarVisualizer label="Cognitive" value={biometrics.cognitive} color="#30D158" />
                    </div>

                    {/* System coherence */}
                    <div className="ace-widget__section">
                        <span className="ace-widget__section-label">System Coherence</span>
                        <RealtimeBarVisualizer label="Coherence" value={agent.cognitive} color="#30D158" />
                        <RealtimeBarVisualizer label="Curvature" value={agent.valenceCurvature} color="#BF5AF2" />
                        <RealtimeBarVisualizer label="Integrity" value={agent.manifoldIntegrity} color="#FF9F0A" />
                    </div>

                    {/* HealthKit */}
                    <div className="ace-widget__section">
                        <span className="ace-widget__section-label">HealthKit</span>
                        <div className="ace-widget__stats-grid">
                            <div className="ace-widget__stat">
                                <span className="ace-widget__stat-label">HR</span>
                                <span className="ace-widget__stat-value">{biometrics.hr} <small>BPM</small></span>
                            </div>
                            <div className="ace-widget__stat">
                                <span className="ace-widget__stat-label">HRV</span>
                                <span className="ace-widget__stat-value">{biometrics.hrv} <small>MS</small></span>
                            </div>
                            <div className="ace-widget__stat">
                                <span className="ace-widget__stat-label">Resp</span>
                                <span className="ace-widget__stat-value">{biometrics.respiratoryRate.toFixed(1)} <small>BR/M</small></span>
                            </div>
                            <div className="ace-widget__stat">
                                <span className="ace-widget__stat-label">Sleep</span>
                                <span className="ace-widget__stat-value">{Math.round(biometrics.sleepEfficiency * 100)}%</span>
                            </div>
                        </div>
                    </div>

                    {/* Harmonic state */}
                    <div className="ace-widget__harmonic">
                        <span className="ace-widget__section-label">Harmonic State</span>
                        <span className={`ace-widget__harmonic-value ${harmonicStatus === 'Stress_Basin' ? 'ace-widget__harmonic-value--stress' : harmonicStatus === 'Loop_Detected' ? 'ace-widget__harmonic-value--loop' : ''}`}>
                            {harmonicStatus.toUpperCase()}
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AffectiveWidget;
