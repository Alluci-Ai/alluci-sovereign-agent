import { useEffect } from 'react';
import { useStore } from '../store/useStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

export const useDaemonStatus = () => {
    const { setDaemonStatus, setHarmonicStatus, setUpdateAvailable, setLatestVersion, setNeedsOnboarding, accessToken } = useStore();

    useEffect(() => {
        let mounted = true;
        const checkDaemon = async () => {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 2000);
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                const headers: any = {};
                const currentToken = useStore.getState().accessToken || localStorage.getItem('alluci_access_token');
                if (currentToken) headers['Authorization'] = `Bearer ${currentToken}`;

                const res = await fetch(`${DAEMON_URL}/api/v1/status`, {
                    signal: controller.signal,
                    headers
                });
                clearTimeout(timeoutId);
                if (mounted) {
                    if (res.ok) {
                        const data = await res.json();
                        if (data.engine_status === 'INITIALIZING') {
                            setDaemonStatus('INITIALIZING');
                        } else {
                            setDaemonStatus('ONLINE');
                        }
                        if (data.harmonic_status) setHarmonicStatus(data.harmonic_status);
                        if (data.update_available !== undefined) setUpdateAvailable(data.update_available);
                        if (data.latest_version !== undefined) setLatestVersion(data.latest_version);

                        // Also check onboarding check
                        const obRes = await fetch(`${DAEMON_URL}/api/v1/onboarding/status`, { signal: controller.signal });
                        if (obRes.ok) {
                            const obData = await obRes.json();
                            setNeedsOnboarding(obData.needs_onboarding);
                        }
                    } else if (res.status === 401) {
                        // If the backend rejects the token, the session has expired or the cryptographic keys rotated.
                        // Clear the invalid token from storage to force the user back to the login screen.
                        localStorage.removeItem('alluci_access_token');
                        localStorage.removeItem('AUTH_TOKEN');
                        useStore.getState().setAccessToken(null);
                        useStore.getState().setActiveView('api');
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [setDaemonStatus, setHarmonicStatus]);
};
