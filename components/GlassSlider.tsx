import React, { useRef, useState, useCallback } from 'react';

/* ═══════════════════════════════════════════════════════════════════════
   GlassSlider — Liquid Glass Tactile Slider
   
   Implements the 4-phase interaction model on a slider control:
   - Idle: Subtle shimmer on thumb
   - Hover: Thumb bulges (1.08x), track brightens
   - Active (Drag): Thumb compresses (0.94x), track refraction increases
   - Release: Elastic snap on thumb, wobble settles
   
   The track fill uses viscous spring animation.
   ═══════════════════════════════════════════════════════════════════════ */

interface GlassSliderProps {
    value: number;
    min?: number;
    max?: number;
    step?: number;
    onChange: (val: number) => void;
    accent?: string;
}

const GlassSlider: React.FC<GlassSliderProps> = ({
    value,
    min = 0,
    max = 1,
    onChange,
    accent = 'var(--accent)'
}) => {
    const trackRef = useRef<HTMLDivElement>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [isHovering, setIsHovering] = useState(false);

    const percent = Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100));

    const handleMove = useCallback((clientX: number) => {
        if (!trackRef.current) return;
        const rect = trackRef.current.getBoundingClientRect();
        const x = clientX - rect.left;
        const newPercent = Math.max(0, Math.min(1, x / rect.width));
        onChange(min + newPercent * (max - min));
    }, [min, max, onChange]);

    const onPointerDown = (e: React.PointerEvent) => {
        setIsDragging(true);
        handleMove(e.clientX);
        e.currentTarget.setPointerCapture(e.pointerId);
        // Haptic: "Surface Break"
        // eslint-disable-next-line no-empty
        try { navigator?.vibrate?.(8); } catch { }
    };

    const onPointerMove = (e: React.PointerEvent) => {
        if (!isDragging) return;
        handleMove(e.clientX);
    };

    const onPointerUp = (e: React.PointerEvent) => {
        setIsDragging(false);
        e.currentTarget.releasePointerCapture(e.pointerId);
        // Haptic: "Release Snap"
        // eslint-disable-next-line no-empty
        try { navigator?.vibrate?.(4); } catch { }
    };

    // Phase-based thumb scale
    const thumbScale = isDragging ? 0.94 : isHovering ? 1.08 : 1;
    // Phase-based transition
    const thumbTransition = isDragging
        ? 'transform 80ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 80ms ease'
        : 'left 0.15s ease, transform 450ms cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 200ms ease';

    return (
        <div
            style={{
                position: 'relative',
                height: 24,
                display: 'flex',
                alignItems: 'center',
                width: '100%',
                cursor: 'pointer',
                touchAction: 'none',
            }}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onMouseEnter={() => setIsHovering(true)}
            onMouseLeave={() => setIsHovering(false)}
        >
            {/* Track */}
            <div
                ref={trackRef}
                style={{
                    position: 'absolute',
                    left: 0, right: 0,
                    height: isDragging ? 5 : isHovering ? 4.5 : 4,
                    borderRadius: 2,
                    background: 'var(--fill-tertiary)',
                    overflow: 'hidden',
                    // Spring transition for track height
                    transition: isDragging
                        ? 'height 80ms cubic-bezier(0.4, 0, 0.2, 1)'
                        : 'height 450ms cubic-bezier(0.34, 1.56, 0.64, 1)',
                }}
            >
                {/* Fill — viscous spring animation */}
                <div
                    style={{
                        height: '100%',
                        borderRadius: 2,
                        width: `${percent}%`,
                        background: `linear-gradient(90deg, ${accent}30, ${accent}50)`,
                        // Refraction shift: more blur during drag
                        backdropFilter: isDragging ? 'blur(6px) saturate(160%)' : 'blur(4px)',
                        // Color bleed at high values
                        boxShadow: percent > 85
                            ? `0 0 8px ${accent}25, 0 0 5px ${accent}18`
                            : `0 0 6px ${accent}18`,
                        transition: isDragging ? 'none' : 'width 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)',
                    }}
                />
            </div>

            {/* Thumb — Liquid Glass Capsule */}
            <div
                style={{
                    position: 'absolute',
                    left: `${percent}%`,
                    transform: `translateX(-50%) scale(${thumbScale})`,
                    width: 16,
                    height: 16,
                    borderRadius: '50%',
                    background: 'var(--bg-elevated)',
                    // Edge highlight: brighten on press
                    border: `2px solid ${isDragging ? 'rgba(255,255,255,0.22)' : 'var(--separator)'}`,
                    // Shadow displacement: closer on press, further on hover
                    boxShadow: isDragging
                        ? '0 0.5px 2px rgba(0,0,0,0.20)'
                        : isHovering
                            ? '0 3px 10px rgba(0,0,0,0.18), 0 1px 3px rgba(0,0,0,0.08)'
                            : '0 1px 4px rgba(0,0,0,0.15)',
                    transition: thumbTransition,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    // Idle shimmer via CSS animation
                    overflow: 'hidden',
                }}
            >
                {/* Inner dot */}
                <div
                    style={{
                        width: 6,
                        height: 6,
                        borderRadius: '50%',
                        background: `${accent}80`,
                        opacity: isDragging ? 1 : isHovering ? 0.9 : 0.7,
                        transition: 'opacity 0.15s ease, transform 450ms cubic-bezier(0.34, 1.56, 0.64, 1)',
                        transform: isDragging ? 'scale(1.2)' : 'scale(1)',
                    }}
                />
                {/* Specular glint on thumb */}
                <div
                    style={{
                        position: 'absolute',
                        inset: 0,
                        borderRadius: 'inherit',
                        background: isHovering
                            ? 'linear-gradient(135deg, rgba(255,255,255,0.15) 0%, transparent 50%)'
                            : 'linear-gradient(135deg, rgba(255,255,255,0.04) 0%, transparent 50%)',
                        transition: 'background 200ms ease',
                        pointerEvents: 'none',
                    }}
                />
            </div>
        </div>
    );
};

export default GlassSlider;
