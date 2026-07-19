import { test, expect } from '@playwright/test';

/**
 * Publication flow E2E test.
 *
 * === Prerequisites ===
 *
 * Before running, make sure the full stack is up:
 *
 *   docker compose up -d
 *
 * Or, if you run services individually:
 *   - API on  http://localhost:8000
 *   - Web on  http://localhost:3000
 *
 * The test assumes a user exists with the credentials below.
 * Create one via the API if needed:
 *
 *   curl -X POST http://localhost:8000/api/v1/auth/register \
 *     -H 'Content-Type: application/json' \
 *     -d '{"email":"admin@test.com","password":"testpass123","full_name":"E2E Admin"}'
 *
 * Then run:
 *
 *   cd tests/e2e
 *   npm install        (first time only)
 *   npx playwright test
 */

const TEST_USER = {
  email: 'admin@test.com',
  password: 'testpass123',
};

test.describe('Publication flow', () => {
  test('log in and view the publications admin page', async ({ page }) => {
    // ------------------------------------------------------------------
    // Step 1 — Visit the login page
    // ------------------------------------------------------------------
    await page.goto('/login');

    // Verify we landed on the login form
    await expect(page.getByRole('heading', { name: 'Sign in' })).toBeVisible();
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();

    // ------------------------------------------------------------------
    // Step 2 — Log in with test credentials
    // ------------------------------------------------------------------
    await page.getByLabel('Email').fill(TEST_USER.email);
    await page.getByLabel('Password').fill(TEST_USER.password);
    await page.getByRole('button', { name: 'Sign in' }).click();

    // After login we should be redirected to /admin.
    // Wait for the admin dashboard (or any admin-only element) to appear.
    await expect(page.getByText('Admin')).toBeVisible({ timeout: 10_000 });

    // ------------------------------------------------------------------
    // Step 3 — Navigate to the Publications page
    // ------------------------------------------------------------------
    await page.getByRole('link', { name: 'Publications' }).click();

    // Verify we're on the publications page
    await expect(
      page.getByRole('heading', { name: 'Publications' }),
    ).toBeVisible({ timeout: 10_000 });

    // The page should show the campaign count, the Refresh button, and
    // either a list of campaigns or the empty / error state.
    await expect(page.getByText(/campaigns?/i)).toBeVisible();

    // ------------------------------------------------------------------
    // Step 4 — Verify core UI elements are present
    // ------------------------------------------------------------------
    await expect(page.getByRole('button', { name: 'Refresh' })).toBeVisible();
  });
});
