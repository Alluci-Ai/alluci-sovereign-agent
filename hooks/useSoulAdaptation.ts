import { useEffect } from 'react';
import { useStore } from '../store/useStore';
import { SoulManifest, SoulConciseness } from '../types';

export const useSoulAdaptation = (geminiService: any) => {
    const {
        biometrics: { emotional: userEmotional, physical: userPhysical, cognitive: userCognitive },
        baseManifest
    } = useStore();

    useEffect(() => {
        if (!baseManifest || !geminiService) return;

        // Deep clone to create a temporary runtime persona
        const dynamicManifest = JSON.parse(JSON.stringify(baseManifest)) as SoulManifest;
        const prefs = dynamicManifest.preferences;

        // 1. Valence Modulation (Emotional State)
        if (userEmotional < 0.4) {
            prefs.empathy = Math.min(1.0, prefs.empathy + 0.4);
            prefs.tone = Math.max(0.0, prefs.tone - 0.3); // Softer
        } else if (userEmotional > 0.8) {
            prefs.creativity = Math.min(1.0, prefs.creativity + 0.2);
        }

        // 2. Cognitive Load Modulation
        if (userCognitive > 0.7) {
            prefs.conciseness = SoulConciseness.CONCISE;
            prefs.verbosity = Math.max(0.0, prefs.verbosity - 0.4);
        } else if (userCognitive < 0.3) {
            prefs.conciseness = SoulConciseness.EXPRESSIVE;
            prefs.verbosity = Math.min(1.0, prefs.verbosity + 0.2);
        }

        // 3. Arousal Modulation (Physical Energy)
        if (userPhysical > 0.8 && userEmotional < 0.4) {
            prefs.tone = 0.2; // Soothing
            prefs.empathy = 1.0;
            prefs.assertiveness = 0.3;
        }

        geminiService.setPersonality(dynamicManifest);
    }, [userEmotional, userPhysical, userCognitive, baseManifest, geminiService]);
};
