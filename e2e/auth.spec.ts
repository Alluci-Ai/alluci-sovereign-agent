import { test, expect, Page } from '@playwright/test';

async function login(page: Page) {
  await page.goto('/');
  const masterKey = process.env.POLYTOPE_MASTER_KEY || '';
  // If onboarding or login modal is visible, complete it
  const loginModal = page.locator('input[type="password"], input[placeholder*="key" i]').first();
  if (await loginModal.isVisible({ timeout: 3000 }).catch(() => false)) {
    await loginModal.fill(masterKey);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);
  }
}

test.describe('Authentication Flows', () => {

  test('login with valid key shows the main UI', async ({ page }) => {
    await login(page);
    await expect(page.locator('.app-shell')).toBeVisible({ timeout: 10_000 });
  });

  test('authenticated user sees sidebar navigation', async ({ page }) => {
    await login(page);
    await expect(page.locator('[class*="sidebar"]')).toBeVisible({ timeout: 5_000 });
  });

  test('page title is correct', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Alluci/i);
  });

});
