
import React, { useState, useEffect, useRef } from 'react';
import { useLiquidVisualizer } from '../hooks/useLiquidGlass';

/* ═══════════════════════════════════════════════════════════════════════
   RealtimeBarVisualizer — Liquid Glass Tactile Visualizer
   
   Implements viscous motion:
   - Inertia-based spring movement with overshoot and rebound
   - Motion blur during fast transitions
   - Color bleed glow at peak values (5pt)
   - Each segment independently animates with spring physics
   ═══════════════════════════════════════════════════════════════════════ */

interface LiquidBarSegmentProps {
    isActive: boolean;
    color: string;
    liquidFill: string;
    liquidGlow: string;
    index: number;
    total: number;
}

/**
 * Individual bar segment with viscous spring motion.
 * Each segment springs independently for a "liquid wave" effect.
 */
const LiquidBarSegment: React.FC<LiquidBarSegmentProps> = ({
    isActive, color, liquidFill, liquidGlow, index, total,
}) => {
    // Each segment uses its own spring for staggered viscous motion
    const targetVal = isActive ? 1 : 0;
    const { value, speed, motionBlurPx, isAtPeak } = useLiquidVisualizer(
        targetVal,
        220 + index * 8, // stiffness increases across bar = ripple effect
        16,
    );

    const opacity = Math.max(0, Math.min(1, value));
    const isMovingFast = speed > 0.5;

    return (
        <div
            className={`lg-visualizer-bar ${isMovingFast ? 'lg-visualizer-bar--moving' : ''} ${isAtPeak ? 'lg-visualizer-bar--peak' : ''}`}
            style={{
                flex: 1,
                backgroundColor: opacity > 0.1 ? liquidFill : 'transparent',
                boxShadow: opacity > 0.1
                    ? `0 0 ${4 + (isAtPeak ? 5 : 0)}px ${liquidGlow}`
                    : 'none',
                borderRadius: 1,
                backdropFilter: opacity > 0.3 ? 'blur(4px) saturate(150%)' : 'none',
                opacity: Math.max(0.05, opacity),
                // Motion blur during fast movement
                filter: isMovingFast ? `blur(${motionBlurPx}px)` : 'none',
                // Liquid Glass spring transition
                transition: 'background-color 0.1s ease',
                '--lg-motion-blur': `${motionBlurPx}px`,
            } as React.CSSProperties}
        />
    );
};

export const RealtimeBarVisualizer: React.FC<{ label: string; value: number; color?: string; onChange?: (v: number) => void }> = ({ label, value, color = 'var(--accent)', onChange }) => {
    const segments = 20;
    const activeSegments = Math.round(value * segments);

    // Convert solid color to a translucent tint for liquid glass
    const getLiquidColor = (solidColor: string, opacity: number) => {
        if (solidColor.startsWith('#')) {
            const hex = solidColor.replace('#', '');
            const r = parseInt(hex.substring(0, 2), 16);
            const g = parseInt(hex.substring(2, 4), 16);
            const b = parseInt(hex.substring(4, 6), 16);
            return `rgba(${r}, ${g}, ${b}, ${opacity})`;
        }
        return solidColor;
    };

    const liquidFill = getLiquidColor(color, 0.35);
    const liquidGlow = getLiquidColor(color, 0.15);

    return (
        <div
            style={{
                display: 'flex', flexDirection: 'column', gap: 3,
                width: '100%', cursor: onChange ? 'pointer' : 'default',
            }}
            onClick={(e) => {
                if (!onChange) return;
                const rect = e.currentTarget.getBoundingClientRect();
                const clickX = e.clientX - rect.left;
                const newVal = Math.max(0, Math.min(1, clickX / rect.width));
                onChange(newVal);
            }}
        >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>{label}</span>
                <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-quaternary)' }}>{(value * 100).toFixed(0)}%</span>
            </div>
            <div style={{
                display: 'flex', height: 4, gap: 1, borderRadius: 2,
                overflow: 'hidden', background: 'var(--fill-quaternary)', padding: 0.5,
            }}>
                {Array.from({ length: segments }).map((_, i) => (
                    <LiquidBarSegment
                        key={i}
                        isActive={i < activeSegments}
                        color={color}
                        liquidFill={liquidFill}
                        liquidGlow={liquidGlow}
                        index={i}
                        total={segments}
                    />
                ))}
            </div>
        </div>
    );
};

export const CircularVisualizer: React.FC<{ stream: MediaStream | null; active: boolean; accent: string }> = ({ stream, active, accent }) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    useEffect(() => {
        if (!stream || !active) return;
        const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
        const analyser = audioCtx.createAnalyser();
        const source = audioCtx.createMediaStreamSource(stream);
        source.connect(analyser);
        analyser.fftSize = 256;
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        let animationId: number;

        // Spring state for viscous bar movement
        const springState = new Float64Array(bufferLength).fill(0);
        const springVelocity = new Float64Array(bufferLength).fill(0);
        const STIFFNESS = 180;
        const DAMPING = 14;

        const draw = () => {
            animationId = requestAnimationFrame(draw);
            analyser.getByteFrequencyData(dataArray);
            const { width, height } = canvas;
            const centerX = width / 2;
            const centerY = height / 2;
            const radius = Math.min(width, height) / 3.5;
            ctx.clearRect(0, 0, width, height);

            // Base circle
            ctx.strokeStyle = 'var(--separator)';
            ctx.lineWidth = 0.5;
            ctx.beginPath(); ctx.arc(centerX, centerY, radius, 0, Math.PI * 2); ctx.stroke();

            for (let i = 0; i < bufferLength; i++) {
                // Spring physics: viscous motion with overshoot & rebound
                const target = (dataArray[i] / 255) * radius * 0.7;
                const force = -STIFFNESS * (springState[i] - target);
                const dampForce = -DAMPING * springVelocity[i];
                springVelocity[i] += (force + dampForce) * 0.016;
                springState[i] += springVelocity[i] * 0.016;
                const barHeight = Math.max(0, springState[i]);

                const speed = Math.abs(springVelocity[i]);
                const angle = (i / bufferLength) * Math.PI * 2;
                const startX = centerX + Math.cos(angle) * radius;
                const startY = centerY + Math.sin(angle) * radius;
                const endX = centerX + Math.cos(angle) * (radius + barHeight);
                const endY = centerY + Math.sin(angle) * (radius + barHeight);

                // Motion blur effect: thicker lines during fast movement
                const motionWidth = 1.5 + Math.min(speed * 0.05, 3);

                // Glow layer (color bleed effect at peaks)
                const isPeak = barHeight / (radius * 0.7) > 0.85;
                if (isPeak) {
                    ctx.strokeStyle = `${accent}15`;
                    ctx.lineWidth = motionWidth + 5; // 5pt color bleed
                    ctx.lineCap = 'round';
                    ctx.beginPath(); ctx.moveTo(startX, startY); ctx.lineTo(endX, endY); ctx.stroke();
                }

                // Outer diffuse stroke
                ctx.strokeStyle = `${accent}25`;
                ctx.lineWidth = motionWidth + 2;
                ctx.lineCap = 'round';
                ctx.beginPath(); ctx.moveTo(startX, startY); ctx.lineTo(endX, endY); ctx.stroke();

                // Inner bright stroke
                ctx.strokeStyle = `${accent}70`;
                ctx.lineWidth = motionWidth;
                ctx.beginPath(); ctx.moveTo(startX, startY); ctx.lineTo(endX, endY); ctx.stroke();
            }
        };
        draw();
        return () => { cancelAnimationFrame(animationId); audioCtx.close(); };
    }, [stream, active, accent]);
    return <canvas ref={canvasRef} width={400} height={400} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />;
};

export type MobileView = 'terminal' | 'vision' | 'system';

export const MobileNav: React.FC<{ active: MobileView; setActive: (v: MobileView) => void }> = ({ active, setActive }) => (
    <nav className="mobile-nav">
        {(['vision', 'terminal', 'system'] as MobileView[]).map(view => (
            <button key={view} onClick={() => setActive(view)}
                className={`mobile-nav__item ${active === view ? 'mobile-nav__item--active' : ''}`}>
                {view.charAt(0).toUpperCase() + view.slice(1)}
            </button>
        ))}
    </nav>
);

export const MobileMenu: React.FC<{ isOpen: boolean; onClose: () => void; onAction: (action: string) => void }> = ({ isOpen, onClose, onAction }) => {
    if (!isOpen) return null;
    const items = [
        { id: 'audit', label: 'Audit Log' },
        { id: 'files', label: 'Files' },
        { id: 'tasks', label: 'Tasks' },
        { id: 'skills', label: 'Skills' },
        { id: 'bridges', label: 'Bridges' },
        { id: 'api', label: 'API Keys' },
        { id: 'soul', label: 'Soul Core' },
    ];

    return (
        <div className="glass-sheet-backdrop" onClick={onClose}>
            <div style={{
                background: 'var(--bg-elevated)',
                borderRadius: 16, border: '1px solid var(--separator)',
                width: '100%', maxWidth: 400,
                padding: '12px 0', boxShadow: 'var(--glass-shadow-lg)',
                // Use spring animation from glass-sheet
                animation: 'lgSheetIn 0.35s var(--lg-spring) forwards',
            }} onClick={e => e.stopPropagation()}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 16px 10px', borderBottom: '1px solid var(--separator)' }}>
                    <span style={{ fontSize: 15, fontWeight: 600 }}>Menu</span>
                    <button onClick={onClose} className="glass-btn" style={{ padding: 4, minWidth: 'auto', fontSize: 14 }}>✕</button>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                    {items.map(item => (
                        <button key={item.id} onClick={() => onAction(item.id)} style={{
                            display: 'flex', alignItems: 'center', padding: '12px 16px',
                            background: 'transparent', border: 'none', cursor: 'pointer',
                            fontSize: 15, fontWeight: 400, color: 'var(--text-primary)',
                            textAlign: 'left',
                            borderBottom: '1px solid var(--separator)',
                            // Liquid Glass spring transition
                            transition: `transform var(--lg-dur-release) var(--lg-spring), background var(--dur-fast) ease`,
                        }}
                            onMouseEnter={e => {
                                e.currentTarget.style.background = 'var(--fill-quaternary)';
                                e.currentTarget.style.transform = 'scale(1.02) translateX(4px)';
                            }}
                            onMouseLeave={e => {
                                e.currentTarget.style.background = 'transparent';
                                e.currentTarget.style.transform = 'scale(1)';
                            }}
                            onMouseDown={e => {
                                e.currentTarget.style.transform = 'scale(0.97)';
                            }}
                            onMouseUp={e => {
                                e.currentTarget.style.transform = 'scale(1.02) translateX(4px)';
                            }}
                        >
                            {item.label}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
};

export const HeartbeatIndicator: React.FC<{ active: boolean }> = ({ active }) => {
    const [pulse, setPulse] = useState(false);
    useEffect(() => {
        if (!active) return;
        const interval = setInterval(() => { setPulse(true); setTimeout(() => setPulse(false), 200); }, 2000);
        return () => clearInterval(interval);
    }, [active]);
    if (!active) return null;
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, opacity: 0.8 }}>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', width: 10, height: 10 }}>
                <div style={{
                    position: 'absolute', inset: 0, borderRadius: '50%', background: 'rgba(48, 209, 88, 0.35)',
                    pointerEvents: 'none',
                    // Liquid Glass spring for pulse expansion
                    transition: `transform var(--lg-dur-release) var(--lg-spring), opacity 0.5s ease`,
                    transform: pulse ? 'scale(1.5)' : 'scale(1)',
                    opacity: pulse ? 0.3 : 0,
                }} />
                <div style={{
                    width: 5, height: 5, borderRadius: '50%',
                    background: 'rgba(48, 209, 88, 0.65)', flexShrink: 0, zIndex: 1,
                    // Subtle liquid compress on pulse
                    transition: `transform var(--lg-dur-release) var(--lg-spring)`,
                    transform: pulse ? 'scale(0.85)' : 'scale(1)',
                }} />
            </div>
            <span className="glass-tag glass-tag--connected" style={{ fontSize: 9, padding: '1px 6px' }}>Active</span>
        </div>
    );
};

export const ExecutionTimeline: React.FC<{ isProcessing: boolean }> = ({ isProcessing }) => {
    const [step, setStep] = useState(0);

    useEffect(() => {
        if (!isProcessing) { setStep(0); return; }
        const interval = setInterval(() => { setStep(s => (s < 4 ? s + 1 : s)); }, 1500);
        return () => clearInterval(interval);
    }, [isProcessing]);

    if (!isProcessing && step === 0) return null;

    const steps = [
        { label: "Parse", status: step > 0 ? 'COMPLETE' : 'ACTIVE' },
        { label: "Plan", status: step > 1 ? 'COMPLETE' : step === 1 ? 'ACTIVE' : 'PENDING' },
        { label: "Execute", status: step > 2 ? 'COMPLETE' : step === 2 ? 'ACTIVE' : 'PENDING' },
        { label: "Review", status: step > 3 ? 'COMPLETE' : step === 3 ? 'ACTIVE' : 'PENDING' }
    ];

    return (
        <div style={{
            width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 3,
            padding: '6px 8px',
            background: 'var(--fill-quaternary)',
            borderRadius: 9999, marginBottom: 16,
            border: '1px solid var(--separator)',
        }}>
            {steps.map((s, i) => {
                const isComplete = s.status === 'COMPLETE';
                const isActive = s.status === 'ACTIVE';
                return (
                    <div key={i} style={{
                        flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center',
                        padding: '4px 6px', borderRadius: 9999,
                        border: `1px solid ${isActive ? 'rgba(255,159,10,0.35)' : 'transparent'}`,
                        background: isComplete ? 'var(--accent-tint)' : isActive ? 'rgba(255,159,10,0.12)' : 'transparent',
                        color: isComplete ? 'var(--accent)' : isActive ? 'var(--accent-warm)' : 'var(--text-quaternary)',
                        // Liquid Glass spring transition for step changes
                        transition: `all var(--lg-dur-release) var(--lg-spring)`,
                        // Active step gets a subtle bulge
                        transform: isActive ? 'scale(1.06)' : isComplete ? 'scale(1)' : 'scale(0.95)',
                    }}>
                        <span style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.02em' }}>{s.label}</span>
                    </div>
                );
            })}
        </div>
    );
};
