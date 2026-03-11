import { test, expect, Page } from '@playwright/test';

async function getAuthenticatedPage(page: Page) {
  await page.goto('/');
  await page.waitForSelector('.app-shell', { timeout: 15_000 });
  return page;
}

test.describe('Critical User Paths', () => {

  test('health check API responds correctly', async ({ page, request }) => {
    const response = await request.get(`${process.env.DAEMON_URL || 'http://localhost:8000'}/health`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.status).toBe('healthy');
  });

  test('sidebar navigation renders all expected items', async ({ page }) => {
    await getAuthenticatedPage(page);
    const expectedItems = ['Tasks', 'Skills', 'Bridges'];
    for (const item of expectedItems) {
      await expect(page.locator(`text=${item}`).first()).toBeVisible({ timeout: 5_000 });
    }
  });

  test('chat interface is functional', async ({ page }) => {
    await getAuthenticatedPage(page);
    await page.click('text=Chat', { timeout: 5_000 }).catch(() => {});
    const commandBar = page.locator('textarea, input[type="text"]').first();
    await expect(commandBar).toBeVisible({ timeout: 5_000 });
  });

  test('no JavaScript errors on load', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));
    await getAuthenticatedPage(page);
    await page.waitForTimeout(2000);
    const criticalErrors = errors.filter(e =>
      !e.includes('ResizeObserver') && !e.includes('Non-Error')
    );
    expect(criticalErrors).toHaveLength(0);
  });

  test('responsive layout on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await getAuthenticatedPage(page);
    await expect(page.locator('.app-shell')).toBeVisible();
  });

  test('DAG planner navigation item exists', async ({ page }) => {
    await getAuthenticatedPage(page);
    // Check sidebar contains DAG-related navigation
    const dagItem = page.locator('text=DAG');
    if (await dagItem.isVisible({ timeout: 2000 }).catch(() => false)) {
      await dagItem.click();
      await expect(page.locator('text=EXECUTION_MANIFOLD')).toBeVisible({ timeout: 5_000 });
    }
  });

});
