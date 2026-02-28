
import { clamp01 } from './alluciCore';

export interface ACENudge {
    id: string;
    type: 'REST' | 'DEEP_WORK' | 'VIBE_CHECK';
    message: string;
    priority: number;
}

/**
 * [ ACE_CONTROLLER ]
 * Monitors biometric state and issues proactive flow assistance nudges.
 */
export class ACEController {
    private lastNudgeTime: number = 0;
    private nudgeCooldown: number = 30000; // 30 seconds for demo purposes

    constructor() { }

    /**
     * [ NUDGE_LOGIC ]
     * Computes necessary interventions based on V (Valence), A (Arousal), and L (Load).
     */
    computeNudge(v: number, a: number, l: number): ACENudge | null {
        const now = Date.now();
        if (now - this.lastNudgeTime < this.nudgeCooldown) return null;

        // 1. Burnout Prevention (High Load + Low Valence)
        if (l > 0.8 && v < 0.3) {
            this.lastNudgeTime = now;
            return {
                id: `nudge_${now}`,
                type: 'REST',
                message: "High cognitive strain detected. Suggesting 5-minute micro-break to preserve manifold integrity.",
                priority: 0.9
            };
        }

        // 2. Flow State Optimization (Medium-High Load + High Valence)
        if (l > 0.6 && v > 0.7 && a > 0.6) {
            this.lastNudgeTime = now;
            return {
                id: `nudge_${now}`,
                type: 'DEEP_WORK',
                message: "Optimal Flow Signature detected. Silencing non-critical social bridges for 15 minutes.",
                priority: 0.7
            };
        }

        // 3. Vibe Check (Very Low Valence)
        if (v < 0.2) {
            this.lastNudgeTime = now;
            return {
                id: `nudge_${now}`,
                type: 'VIBE_CHECK',
                message: "Manifesting positive resonance shift. Would you like to switch to an expansive music manifold?",
                priority: 0.5
            };
        }

        return null;
    }
}
