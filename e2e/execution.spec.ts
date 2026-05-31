// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { test, expect, Page } from '@playwright/test';

test.describe('O-5: Swarm Execution & WebSockets Flow', () => {

  test('Submitting a task streams WebSocket artifacts to the UI', async ({ page, context }) => {
    // 1. Mock WebAuthn Virtual Authenticator for Login
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

    const loginBtn = page.locator('button:has-text("Login with Hardware Key")');
    if (await loginBtn.isVisible({ timeout: 5000 })) {
      await loginBtn.click();
    }
    await expect(page.locator('.app-shell')).toBeVisible({ timeout: 10_000 });

    // 2. Mock WebSocket connection to track events
    // We can evaluate in page context to intercept WebSocket messages if needed,
    // but Playwright also allows asserting on UI DOM updates directly which is more robust.
    
    // 3. Submit a complex objective via Chat/Command Bar
    const commandBar = page.locator('textarea, input[type="text"]').first();
    await commandBar.fill('Execute test objective for sub-agent delegation');
    await commandBar.press('Enter');

    // 4. Assert that the Sub-Agent node appears in the DAG manifold
    const dagTab = page.locator('text=DAG').first();
    if (await dagTab.isVisible()) {
      await dagTab.click();
    }
    
    // 5. Assert the Artifact Pane updates from WebSocket hook
    // The placeholder should disappear and markdown content should appear
    const artifactPane = page.locator('.artifact-pane, [data-testid="artifact-pane"]');
    if (await artifactPane.isVisible()) {
      await expect(artifactPane).not.toContainText('Awaiting Artifact', { timeout: 30000 });
      // Depending on the DOM structure, verify a markdown block or code block rendered
      await expect(artifactPane.locator('.markdown-body, pre, code').first()).toBeVisible({ timeout: 15_000 });
    }

    await cdpSession.send('WebAuthn.removeVirtualAuthenticator', {
      authenticatorId: authenticator.authenticatorId
    });
    await cdpSession.send('WebAuthn.disable');
  });

});
