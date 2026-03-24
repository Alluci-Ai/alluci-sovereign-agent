// lib/bridgeAuth.ts — RE-APPLIED FIX

import { getCsrfToken } from '../csrfStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL;

export async function saveBridgeCredentials(bridgeId: string, credentials: Record<string, string>) {
  const token = localStorage.getItem('alluci_access_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Ensure CSRF protection for credential mutation
  const csrfToken = await getCsrfToken(DAEMON_URL, token || '');
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken;
  }

  const res = await fetch(`${DAEMON_URL}/api/v1/auth/bridge/${bridgeId}/save`, {
    method: 'POST',
    headers: headers,
    body: JSON.stringify(credentials),
    credentials: 'include'
  });

  if (!res.ok) throw new Error('Failed to save bridge credentials');
  return res.json();
}

export async function activateBridge(bridgeId: string) {
  const token = localStorage.getItem('alluci_access_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Ensure CSRF protection for bridge activation state
  const csrfToken = await getCsrfToken(DAEMON_URL, token || '');
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken;
  }

  const res = await fetch(`${DAEMON_URL}/api/v1/bridge/${bridgeId}/activate`, {
    method: 'POST',
    headers: headers,
    credentials: 'include'
  });

  if (!res.ok) throw new Error('Failed to activate bridge');
  return res.json();
}
