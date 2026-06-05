let _csrfToken: string | null = null;
let _refreshTimeout: ReturnType<typeof setTimeout> | null = null;

export const setCsrfToken = (token: string | null) => {
  _csrfToken = token;
};

export const getCsrfToken = async (daemonUrl: string, accessToken: string | null, forceRefresh = false): Promise<string | null> => {
  if (_csrfToken && !forceRefresh) return _csrfToken;
  try {
    const headers: Record<string, string> = {
        'Accept': 'application/json'
    };
    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }
    const res = await fetch(`${daemonUrl}/api/v1/auth/csrf-token`, {
      credentials: 'include',
      headers: headers
    });
    if (!res.ok) {
        console.warn("CSRF Token Fetch Failed:", res.status);
        return null;
    }
    const data = await res.json();
    _csrfToken = data.csrf_token;
    
    // Auto-refresh token 1 minute before typical expiration (assuming 15m expiration, refresh at 14m)
    if (_refreshTimeout) clearTimeout(_refreshTimeout);
    _refreshTimeout = setTimeout(() => {
        getCsrfToken(daemonUrl, accessToken, true).catch(console.error);
    }, 14 * 60 * 1000);

    return _csrfToken;
  } catch (err) {
    console.error("Failed to fetch CSRF token:", err);
    return null;
  }
};

export const refreshCsrfToken = async (daemonUrl: string, accessToken: string | null): Promise<string | null> => {
  return getCsrfToken(daemonUrl, accessToken, true);
};
