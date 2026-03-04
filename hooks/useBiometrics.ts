import { useEffect } from 'react';
import { useStore } from '../store/useStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

export const useBiometrics = () => {
    const { biometrics, updateBiometrics, setHarmonicStatus } = useStore();

    useEffect(() => {
        // [ BIOMETRIC_SIMULATION ]
        // Only active in demo mode to prevent production data pollution
        if (import.meta.env.VITE_DEMO_MODE !== 'true') return;

        const interval = setInterval(async () => {
            // Subtle variations
            const nextHR = Math.floor(70 + Math.random() * 10);
            const nextHRV = Math.floor(50 + Math.random() * 15);
            const nextRR = 12 + Math.random() * 4;

            updateBiometrics({ hr: nextHR, hrv: nextHRV, respiratoryRate: nextRR });

            // Push to backend
            try {
                const res = await fetch(`${DAEMON_URL}/api/bridge/iwatch/biometrics`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        hr: nextHR,
                        hrv: nextHRV,
                        respiratory_rate: nextRR,
                        sleep_efficiency: biometrics.sleepEfficiency,
                        valence: biometrics.emotional,
                        arousal: biometrics.physical,
                        focus: biometrics.cognitive
                    })
                });
                const data = await res.json();
                if (data.flow_intervention) {
                    if (data.flow_intervention.mode === 'RECOVERY_MODE') {
                        setHarmonicStatus('Stress_Basin');
                    } else if (data.flow_intervention.mode === 'PEAK_PERFORMANCE') {
                        setHarmonicStatus('Nominal');
                    }
                }
            } catch (e) {
                // Silently fail or log to audit
            }
        }, 5000);
        return () => clearInterval(interval);
    }, [
        biometrics.emotional,
        biometrics.physical,
        biometrics.cognitive,
        biometrics.sleepEfficiency,
        updateBiometrics,
        setHarmonicStatus
    ]);
};
