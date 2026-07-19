import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E configuration for the RealEstate project.
 *
 * Prerequisites:
 *   docker compose up   (postgres, redis, minio, api, worker, web)
 *
 * The web app runs at http://localhost:3000 and the API at http://localhost:8000.
 */
export default defineConfig({
  testDir: '.',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['html', { outputFolder: 'playwright-report' }], ['list']],

  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // The web server is started externally via docker compose; no webServer config here.
});
