import { useRef, useCallback, useState, useEffect } from 'react';

/* ═══════════════════════════════════════════════════════════════════════
   useLiquidGlass — Tactile Interaction Hook
   
   Implements the 4-stage Liquid Glass interaction model:
   1. Idle:    Subtle specular glint shimmer (8 s loop)
   2. Hover:   Lensing expansion — the glass "bulges" (scale 1.05, spring)
   3. Active:  Gel compression — glass flattens, refraction increases (scale 0.96)
   4. Release: Elastic snap — wobble then settle (damping 0.7, stiffness 200)

   Also provides:
   - Light-tracking specular glint (P_glint = Input_xy * 0.1 + center)
   - Haptic feedback (Vibration API) for surface-break / bottom-out / release
   - CSS custom-property injection for per-element refraction shifts
   ═══════════════════════════════════════════════════════════════════════ */

/** Interaction state machine */
type GlassPhase = 'idle' | 'hover' | 'active' | 'release';

interface LiquidGlassOptions {
    /** Maximum compression (default: 0.96 – never more than 10% of original) */
    compressScale?: number;
    /** Hover bulge scale (default: 1.05) */
    bulgeScale?: number;
    /** Spring stiffness (default: 300) */
    stiffness?: number;
    /** Spring damping (default: 20) */
    damping?: number;
    /** Enable haptic feedback (default: true) */
    haptics?: boolean;
    /** Variant: 'button' | 'card' | 'nav' | 'slider' | 'tag' | 'input' */
    variant?: 'button' | 'card' | 'nav' | 'slider' | 'tag' | 'input';
    /** Disable all tactile effects */
    disabled?: boolean;
    /** Extra blur increase (%) during press for refraction shift */
    refractionBoost?: number;
}

interface LiquidGlassReturn {
    ref: React.RefObject<HTMLElement | null>;
    style: React.CSSProperties;
    handlers: {
        onMouseEnter: (e: React.MouseEvent) => void;
        onMouseLeave: (e: React.MouseEvent) => void;
        onMouseMove: (e: React.MouseEvent) => void;
        onMouseDown: (e: React.MouseEvent) => void;
        onMouseUp: (e: React.MouseEvent) => void;
        onTouchStart: (e: React.TouchEvent) => void;
        onTouchEnd: (e: React.TouchEvent) => void;
    };
    phase: GlassPhase;
    /** CSS class suffix for the current phase */
    phaseClass: string;
    /** The glint gradient string */
    glintGradient: string;
}

/* ── Spring physics (CSS-approachable cubic-bezier approximations) ───── */

/** Attempt to trigger haptic feedback via Vibration API */
function hapticPulse(pattern: number | number[]) {
    try {
        if ('vibrate' in navigator) {
            navigator.vibrate(pattern);
        }
    } catch {
        /* Silently fail on unsupported platforms */
    }
}

/** Clamp a number between min and max */
function clamp(n: number, min: number, max: number) {
    return Math.max(min, Math.min(max, n));
}

/* ── Hook ────────────────────────────────────────────────────────────── */

export function useLiquidGlass(options: LiquidGlassOptions = {}): LiquidGlassReturn {
    const {
        compressScale = 0.96,
        bulgeScale = 1.05,
        stiffness: _stiffness = 300,
        damping: _damping = 20,
        haptics = true,
        variant = 'button',
        disabled = false,
        refractionBoost = 15,
    } = options;

    const ref = useRef<HTMLElement | null>(null);
    const [phase, setPhase] = useState<GlassPhase>('idle');
    const [glintPos, setGlintPos] = useState({ x: 50, y: 50 }); // percentage
    const releaseTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
    const shimmerPhase = useRef(0);

    // Idle shimmer: update CSS custom property via a slow animation frame
    useEffect(() => {
        if (disabled) return;
        let raf: number;
        const tick = () => {
            shimmerPhase.current = (shimmerPhase.current + 0.0008) % 1; // ~8 s full cycle
            if (ref.current && phase === 'idle') {
                const offset = Math.sin(shimmerPhase.current * Math.PI * 2) * 30 + 50;
                ref.current.style.setProperty('--lg-shimmer-offset', `${offset}%`);
            }
            raf = requestAnimationFrame(tick);
        };
        raf = requestAnimationFrame(tick);
        return () => cancelAnimationFrame(raf);
    }, [disabled, phase]);

    /* ── Phase transitions ──────────────────────────────────────────── */

    const onMouseEnter = useCallback((e: React.MouseEvent) => {
        if (disabled) return;
        setPhase('hover');
    }, [disabled]);

    const onMouseLeave = useCallback((_e: React.MouseEvent) => {
        if (disabled) return;
        setPhase('idle');
        setGlintPos({ x: 50, y: 50 });
    }, [disabled]);

    const onMouseMove = useCallback((e: React.MouseEvent) => {
        if (disabled || !ref.current) return;
        const rect = ref.current.getBoundingClientRect();
        const relX = ((e.clientX - rect.left) / rect.width) * 100;
        const relY = ((e.clientY - rect.top) / rect.height) * 100;
        // Formula: P_glint = (Input_xy * 0.1) + Center_offset
        const gx = clamp(relX * 0.1 + 45, 0, 100);
        const gy = clamp(relY * 0.1 + 45, 0, 100);
        setGlintPos({ x: gx, y: gy });
    }, [disabled]);

    const onMouseDown = useCallback((_e: React.MouseEvent) => {
        if (disabled) return;
        setPhase('active');
        // Haptic: "Surface Break" — sharp transient
        if (haptics) hapticPulse(8);
        // Haptic: "Bottom Out" — slightly deeper continuous
        if (haptics) setTimeout(() => hapticPulse([5, 10, 12]), 60);
    }, [disabled, haptics]);

    const onMouseUp = useCallback((_e: React.MouseEvent) => {
        if (disabled) return;
        setPhase('release');
        // Haptic: "Release Snap" — very light tick
        if (haptics) hapticPulse(4);
        // After elastic snap settles, return to hover (still on element)
        clearTimeout(releaseTimer.current);
        releaseTimer.current = setTimeout(() => {
            setPhase(prev => prev === 'release' ? 'hover' : prev);
        }, 400);
    }, [disabled, haptics]);

    const onTouchStart = useCallback((_e: React.TouchEvent) => {
        if (disabled) return;
        setPhase('active');
        if (haptics) hapticPulse(8);
    }, [disabled, haptics]);

    const onTouchEnd = useCallback((_e: React.TouchEvent) => {
        if (disabled) return;
        setPhase('release');
        if (haptics) hapticPulse(4);
        clearTimeout(releaseTimer.current);
        releaseTimer.current = setTimeout(() => {
            setPhase(prev => prev === 'release' ? 'idle' : prev);
        }, 400);
    }, [disabled, haptics]);

    /* ── Derived values ─────────────────────────────────────────────── */

    // Variant-based adjustments
    const variantMod = {
        button: { bulge: bulgeScale, compress: compressScale },
        card: { bulge: 1.015, compress: 0.985 },
        nav: { bulge: 1.03, compress: 0.97 },
        slider: { bulge: 1.08, compress: 0.94 },
        tag: { bulge: 1.04, compress: 0.97 },
        input: { bulge: 1.0, compress: 1.0 }, // inputs don't scale, just glow
    }[variant];

    // Scale per phase
    const scaleMap: Record<GlassPhase, number> = {
        idle: 1,
        hover: variantMod.bulge,
        active: variantMod.compress,
        release: 1.02, // slight overshoot during elastic snap
    };

    // Shadow displacement: closer and sharper on press
    const shadowMap: Record<GlassPhase, string> = {
        idle: 'var(--glass-shadow)',
        hover: '0 4px 16px rgba(0,0,0,0.18), 0 1px 4px rgba(0,0,0,0.10)',
        active: '0 1px 4px rgba(0,0,0,0.22), 0 0.5px 2px rgba(0,0,0,0.14)',
        release: '0 3px 12px rgba(0,0,0,0.16), 0 1px 3px rgba(0,0,0,0.08)',
    };

    // Backdrop-filter refraction shift
    const blurMap: Record<GlassPhase, string> = {
        idle: 'blur(10px)',
        hover: 'blur(12px)',
        active: `blur(${10 * (1 + refractionBoost / 100)}px)`,
        release: 'blur(11px)',
    };

    // Transition/animation per phase — spring physics via cubic-bezier
    // Spring: stiffness 300, damping 20 → approx cubic-bezier(0.34, 1.56, 0.64, 1)
    const transitionMap: Record<GlassPhase, string> = {
        idle: 'transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease, backdrop-filter 0.3s ease, border-color 0.2s ease',
        hover: 'transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease, backdrop-filter 0.2s ease, border-color 0.2s ease',
        active: 'transform 0.08s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.08s ease, backdrop-filter 0.08s ease, border-color 0.08s ease',
        release: 'transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.35s ease, backdrop-filter 0.3s ease, border-color 0.2s ease',
    };

    // Edge highlight: brighten border by 20% on press
    const borderBrightnessMap: Record<GlassPhase, string> = {
        idle: '',
        hover: '',
        active: 'rgba(255,255,255,0.18)',
        release: '',
    };

    // Specular glint gradient
    const glintGradient = phase === 'idle'
        ? `linear-gradient(135deg, rgba(255,255,255,0.02) 0%, transparent 40%, rgba(255,255,255,0.015) 100%)`
        : `radial-gradient(circle at ${glintPos.x}% ${glintPos.y}%, rgba(255,255,255,${phase === 'active' ? 0.06 : 0.12}) 0%, transparent 60%)`;

    // Build transform
    const scale = scaleMap[phase];
    const translateZ = phase === 'active' ? '-4px' : phase === 'hover' ? '2px' : '0px';
    const transform = `scale(${scale}) translateZ(${translateZ})`;

    /* ── Composite style ────────────────────────────────────────────── */

    const style: React.CSSProperties = disabled ? {} : {
        transform,
        transition: transitionMap[phase],
        boxShadow: shadowMap[phase],
        backdropFilter: blurMap[phase],
        WebkitBackdropFilter: blurMap[phase],
        willChange: 'transform, box-shadow, backdrop-filter',
        ...(borderBrightnessMap[phase] ? { borderColor: borderBrightnessMap[phase] } : {}),
    };

    // Phase → CSS class suffix
    const phaseClass = disabled ? '' : `lg-${phase}`;

    return {
        ref,
        style,
        handlers: {
            onMouseEnter,
            onMouseLeave,
            onMouseMove,
            onMouseDown,
            onMouseUp,
            onTouchStart,
            onTouchEnd,
        },
        phase,
        phaseClass,
        glintGradient,
    };
}

/* ═══════════════════════════════════════════════════════════════════════
   useLiquidVisualizer — Viscous Motion for Visualizer Bars
   
   Implements inertia-based movement with overshoot, rebound, motion 
   blur, and color bleed for visualizer elements.
   ═══════════════════════════════════════════════════════════════════════ */

interface VisualiserSpringState {
    current: number;
    velocity: number;
    target: number;
}

export function useLiquidVisualizer(
    targetValue: number,
    stiffness = 180,
    damping = 14,
) {
    const spring = useRef<VisualiserSpringState>({
        current: targetValue,
        velocity: 0,
        target: targetValue,
    });
    const [display, setDisplay] = useState(targetValue);
    const [speed, setSpeed] = useState(0);
    const raf = useRef<number>(undefined);

    useEffect(() => {
        spring.current.target = targetValue;

        const step = () => {
            const s = spring.current;
            const force = -stiffness * (s.current - s.target);
            const dampForce = -damping * s.velocity;
            const acceleration = force + dampForce;
            s.velocity += acceleration * 0.016; // ~60 FPS
            s.current += s.velocity * 0.016;

            const currentSpeed = Math.abs(s.velocity);
            setSpeed(currentSpeed);
            setDisplay(s.current);

            if (Math.abs(s.current - s.target) > 0.001 || currentSpeed > 0.01) {
                raf.current = requestAnimationFrame(step);
            } else {
                s.current = s.target;
                s.velocity = 0;
                setDisplay(s.target);
                setSpeed(0);
            }
        };

        cancelAnimationFrame(raf.current!);
        raf.current = requestAnimationFrame(step);
        return () => cancelAnimationFrame(raf.current!);
    }, [targetValue, stiffness, damping]);

    // Motion blur: directional blur proportional to velocity
    const motionBlurPx = clamp(speed * 2, 0, 6);
    // Color bleed glow: 5pt at peak
    const isAtPeak = display > 0.85;
    const colorBleedPx = isAtPeak ? 5 : 0;

    return {
        value: display,
        speed,
        motionBlurPx,
        colorBleedPx,
        isAtPeak,
    };
}

export default useLiquidGlass;
