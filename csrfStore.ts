
let _csrfToken: string | null = null;

export const setCsrfToken = (token: string | null) => {
  _csrfToken = token;
};

export const getCsrfToken = async (daemonUrl: string, accessToken: string | null): Promise<string | null> => {
  if (_csrfToken) return _csrfToken;
  try {
    const headers: Record<string, string> = {};
    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }
    const res = await fetch(`${daemonUrl}/api/v1/auth/csrf-token`, {
      credentials: 'include',
      headers: headers
    });
    if (!res.ok) return null;
    const data = await res.json();
    _csrfToken = data.csrf_token;
    return _csrfToken;
  } catch (err) {
    console.error("Failed to fetch CSRF token:", err);
    return null;
  }
};
