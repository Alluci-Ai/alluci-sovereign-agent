import { useEffect } from 'react';
import { useStore } from '../store/useStore';

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

export const useBiometrics = () => {
    const { biometrics, updateBiometrics, setHarmonicStatus } = useStore();

    useEffect(() => {
        // [ BIOMETRIC_INTEGRATION ]
        // We now rely on the WebSocket gateway pushing 'system.telemetry' events from the backend.
        // The mock generator has been removed for production readiness.
        
        const handleTelemetry = (event: CustomEvent) => {
            const data = event.detail;
            
            if (data) {
                updateBiometrics({ 
                    hr: data.hr ?? biometrics.hr, 
                    hrv: data.hrv ?? biometrics.hrv, 
                    respiratoryRate: data.respiratory_rate ?? biometrics.respiratoryRate,
                    emotional: data.valence ?? biometrics.emotional,
                    physical: data.arousal ?? biometrics.physical,
                    cognitive: data.focus ?? biometrics.cognitive
                });
            }
            
            // Sync Harmonic Status based on Flow Intervention mode
            if (data.flow_intervention) {
                if (data.flow_intervention.mode === 'RECOVERY_MODE') {
                    setHarmonicStatus('Stress_Basin');
                } else if (data.flow_intervention.mode === 'PEAK_PERFORMANCE') {
                    setHarmonicStatus('Nominal');
                }
            }
        };

        // Listen for standard WebSocket telemetry events dispatched by the App container
        window.addEventListener('alluci.system.telemetry', handleTelemetry as EventListener);
        
        return () => {
            window.removeEventListener('alluci.system.telemetry', handleTelemetry as EventListener);
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [updateBiometrics, setHarmonicStatus, biometrics.hr, biometrics.hrv, biometrics.respiratoryRate]);
};
