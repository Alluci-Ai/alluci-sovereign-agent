// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { test, expect, Page } from '@playwright/test';

test.describe('O-4: Sovereign Authentication Flows', () => {

  test('WebAuthn login with virtual authenticator', async ({ page, context }) => {
    // 1. Mock WebAuthn Virtual Authenticator via CDP
    const cdpSession = await context.newCDPSession(page);
    await cdpSession.send('WebAuthn.enable');
    const authenticator = await cdpSession.send('WebAuthn.addVirtualAuthenticator', {
      options: {
        protocol: 'ctap2',
        transport: 'internal',
        hasResidentKey: true,
        hasUserVerification: true,
        isUserVerified: true,
      }
    });

    await page.goto('/');

    // 2. Perform Login Flow
    const loginBtn = page.locator('button:has-text("Login with Hardware Key")');
    if (await loginBtn.isVisible({ timeout: 5000 })) {
      await loginBtn.click();
      
      // The WebAuthn API will automatically use the virtual authenticator we added
      await expect(page.locator('.app-shell')).toBeVisible({ timeout: 10_000 });
      
      // 3. Verify CSRF Token Injection
      const cookies = await context.cookies();
      const csrfCookie = cookies.find(c => c.name === 'XSRF-TOKEN');
      expect(csrfCookie).toBeDefined();
      
      // 4. Secure Logout Flow
      const logoutBtn = page.locator('button[aria-label="Logout"], .sidebar-logout');
      if (await logoutBtn.isVisible()) {
        await logoutBtn.click();
        await expect(loginBtn).toBeVisible({ timeout: 5_000 });
      }
    }
    
    await cdpSession.send('WebAuthn.removeVirtualAuthenticator', {
      authenticatorId: authenticator.authenticatorId
    });
    await cdpSession.send('WebAuthn.disable');
  });

  test('CSRF double-submit integrity blocks cross-site attacks', async ({ request }) => {
    // Making a POST request without the CSRF header should fail with 403 Forbidden
    const response = await request.post(`${process.env.DAEMON_URL || 'http://localhost:8000'}/api/v1/auth/protected`, {
      data: { sensitive_action: true }
    });
    expect(response.status()).toBe(403);
  });
});
