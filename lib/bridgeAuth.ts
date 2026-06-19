// lib/bridgeAuth.ts — RE-APPLIED FIX

import { getCsrfToken } from '../csrfStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

export async function saveBridgeCredentials(bridgeId: string, credentials: Record<string, string>, token?: string) {
  const activeToken = token || localStorage.getItem('alluci_access_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (activeToken) {
    headers['Authorization'] = `Bearer ${activeToken}`;
  }

  // Ensure CSRF protection for credential mutation
  let csrfToken = await getCsrfToken(DAEMON_URL, activeToken || '');
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken;
  }

  let res = await fetch(`${DAEMON_URL}/api/v1/auth/bridge/${bridgeId}/save`, {
    method: 'POST',
    headers: headers,
    body: JSON.stringify(credentials),
    credentials: 'include'
  });

  // If CSRF token is rejected (e.g. backend restarted), force refresh and retry once
  if (res.status === 403) {
      console.warn("Possible CSRF token mismatch, forcing refresh...");
      csrfToken = await getCsrfToken(DAEMON_URL, activeToken || '', true);
      if (csrfToken) {
          headers['X-CSRF-Token'] = csrfToken;
          res = await fetch(`${DAEMON_URL}/api/v1/auth/bridge/${bridgeId}/save`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(credentials),
            credentials: 'include'
          });
      }
  }

  if (!res.ok) {
    let errorText = "Unknown error";
    try {
        const errorData = await res.json();
        errorText = errorData.detail || JSON.stringify(errorData);
    } catch (e) {
        errorText = await res.text();
    }
    throw new Error(`Failed to save bridge credentials (${res.status}): ${errorText}`);
  }
  return res.json();
}

export async function activateBridge(bridgeId: string, token?: string) {
  const activeToken = token || localStorage.getItem('alluci_access_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (activeToken) {
    headers['Authorization'] = `Bearer ${activeToken}`;
  }

  // Ensure CSRF protection for bridge activation state
  const csrfToken = await getCsrfToken(DAEMON_URL, activeToken || '');
  if (csrfToken) {
    headers['X-CSRF-Token'] = csrfToken;
  }

  const res = await fetch(`${DAEMON_URL}/api/v1/bridge/${bridgeId}/activate`, {
    method: 'POST',
    headers: headers,
    credentials: 'include'
  });

  if (!res.ok) {
    let errorText = await res.text();
    try {
      const parsed = JSON.parse(errorText);
      errorText = parsed.detail || errorText;
    } catch (e) {
      // Not JSON
    }
    throw new Error(`Failed to activate bridge (${res.status}): ${errorText}`);
  }
  return res.json();
}
