import { useState } from 'react';
import { useStore } from '../store/useStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || '';

export const useIdentityAuth = () => {
    const { setAccessToken } = useStore();
    const [masterKeyInput, setMasterKeyInput] = useState("");
    const [isAuthenticating, setIsAuthenticating] = useState(false);
    const [authStatus, setAuthStatus] = useState<string | null>(null);

    const handleDaemonLogin = async () => {
        setIsAuthenticating(true);
        setAuthStatus(null);
        try {
            const res = await fetch(`${DAEMON_URL}/api/v1/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ key: masterKeyInput }),
                credentials: 'include'
            });
            if (res.ok) {
                const data = await res.json();
                setAuthStatus("SUCCESS: Sovereign Identity Verified.");
                localStorage.setItem('alluci_access_token', data.access_token); // Persist for services
                setAccessToken(data.access_token);
                setMasterKeyInput("");
            } else {
                setAuthStatus("FAILURE: Invalid Key.");
            }
        } catch (e) {
            setAuthStatus("ERROR: Daemon Unreachable.");
        } finally {
            setIsAuthenticating(false);
        }
    };

    return {
        masterKeyInput,
        setMasterKeyInput,
        isAuthenticating,
        authStatus,
        handleDaemonLogin
    };
};
