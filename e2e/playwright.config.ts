import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['junit', { outputFile: 'e2e-results.xml' }],
  ],
  use: {
    baseURL:  process.env.E2E_BASE_URL || 'http://localhost:3000',
    trace:    'on-first-retry',
    video:    'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile-chrome', use: { ...devices['Pixel 5'] } },
  ],
  webServer: process.env.CI ? undefined : {
    command: 'npm run dev',
    port:    3000,
    reuseExistingServer: !process.env.CI,
  },
});
