const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

// Store credentials in vault (called before activateBridge)
export async function saveBridgeCredentials(
    id: string, creds: Record<string, any>, token: string
): Promise<boolean> {
    const res = await fetch(`${DAEMON_URL}/api/channels/${id}/config`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(creds),
    });
    return res.ok;
}

// Activate bridge adapter with stored credentials
export async function activateBridge(
    id: string, token: string
): Promise<{ connected: boolean; alias?: string; profileImg?: string; error?: string }> {
    const res = await fetch(`${DAEMON_URL}/api/channels/${id}/connect`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        credentials: 'include',
    });
    if (!res.ok) return { connected: false, error: await res.text() };
    return res.json();
}
