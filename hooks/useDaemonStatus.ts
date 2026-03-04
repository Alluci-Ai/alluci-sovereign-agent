import { useEffect } from 'react';
import { useStore } from '../store/useStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

export const useDaemonStatus = () => {
    const { setDaemonStatus, setHarmonicStatus, setUpdateAvailable, setLatestVersion, setNeedsOnboarding, accessToken } = useStore();

    useEffect(() => {
        let mounted = true;
        const checkDaemon = async () => {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 2000);
                const headers: any = {};
                if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`;

                const res = await fetch(`${DAEMON_URL}/status`, {
                    signal: controller.signal,
                    headers
                });
                clearTimeout(timeoutId);
                if (mounted) {
                    if (res.ok) {
                        const data = await res.json();
                        setDaemonStatus('ONLINE');
                        if (data.harmonic_status) setHarmonicStatus(data.harmonic_status);
                        if (data.update_available !== undefined) setUpdateAvailable(data.update_available);
                        if (data.latest_version !== undefined) setLatestVersion(data.latest_version);

                        // Also check onboarding check
                        const obRes = await fetch(`${DAEMON_URL}/api/onboarding/status`, { signal: controller.signal });
                        if (obRes.ok) {
                            const obData = await obRes.json();
                            setNeedsOnboarding(obData.needs_onboarding);
                        }
                    } else if (res.status === 401) {
                        // Keep online but maybe restricted? Or just set ONLINE if we can talk to it.
                        // Usually 401 means the server is UP, but we are just not authorized.
                        setDaemonStatus('ONLINE');
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
