import { useEffect } from 'react';
import { useStore } from '../store/useStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

export const useDaemonStatus = () => {
    const { setDaemonStatus, setHarmonicStatus } = useStore();

    useEffect(() => {
        let mounted = true;
        const checkDaemon = async () => {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 2000);
                const res = await fetch(`${DAEMON_URL}/system/status`, { signal: controller.signal });
                clearTimeout(timeoutId);
                if (mounted) {
                    if (res.ok) {
                        const data = await res.json();
                        setDaemonStatus('ONLINE');
                        if (data.harmonic_status) setHarmonicStatus(data.harmonic_status);
                    } else {
                        setDaemonStatus('OFFLINE');
                    }
                }
            } catch (e) {
                if (mounted) setDaemonStatus('OFFLINE');
            }
        };
        checkDaemon();
        const interval = setInterval(checkDaemon, 5000);
        return () => {
            mounted = false;
            clearInterval(interval);
        };
    }, [setDaemonStatus, setHarmonicStatus]);
};
