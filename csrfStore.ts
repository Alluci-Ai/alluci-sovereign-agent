let _csrfToken: string | null = null;
let _csrfTokenFetchedAt: number = 0;

// Token is considered fresh for 10 minutes
const TOKEN_FRESH_MS = 10 * 60 * 1000;

export const setCsrfToken = (token: string | null) => {
  _csrfToken = token;
  _csrfTokenFetchedAt = token ? Date.now() : 0;
};

const _isTokenFresh = (): boolean => {
  return !!_csrfToken && (Date.now() - _csrfTokenFetchedAt) < TOKEN_FRESH_MS;
};

export const getCsrfToken = async (daemonUrl: string, accessToken: string | null, forceRefresh = false): Promise<string | null> => {
  // Return cached token only if it's fresh and no force-refresh requested
  if (_isTokenFresh() && !forceRefresh) return _csrfToken;

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
    _csrfTokenFetchedAt = Date.now();

    return _csrfToken;
  } catch (err) {
    console.error("Failed to fetch CSRF token:", err);
    return null;
  }
};

export const refreshCsrfToken = async (daemonUrl: string, accessToken: string | null): Promise<string | null> => {
  return getCsrfToken(daemonUrl, accessToken, true);
};
