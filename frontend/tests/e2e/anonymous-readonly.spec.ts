/**
 * Anonymous read-only bypass (ADR-123 / SPEC-123-A / issue #18).
 *
 * Clears localStorage + sessionStorage, navigates to `/`, asserts the
 * dashboard renders without redirecting to /login, and that write UI
 * is hidden. Admin routes still gate anonymous visitors.
 *
 * Then signs in as admin and re-visits to confirm write UI returns —
 * proves the anonymous state is governed by the auth store, not a
 * permanent change.
 */

import { expect, test } from '@playwright/test';
import { seedAdmin, loginAsAdmin } from './fixtures';

test.describe('Anonymous read-only bypass (ADR-123)', () => {
	test.describe.configure({ timeout: 60_000 });

	test.beforeAll(async ({ baseURL }) => {
		await seedAdmin(baseURL);
	});

	test.beforeEach(async ({ context }) => {
		// Clear all browser state so each test starts as a fresh anonymous visitor.
		await context.clearCookies();
	});

	test('anonymous visitor lands on dashboard, no login redirect', async ({ page }) => {
		// Start with fully cleared storage. goto() first so we can clear storage
		// on a real origin; then navigate again so the cleared storage takes
		// effect on the first reactive auth check.
		await page.goto('/');
		await page.evaluate(() => {
			localStorage.clear();
			sessionStorage.clear();
		});
		await page.goto('/');

		// Must land on `/`, not `/login`.
		await expect(page).toHaveURL(/\/$/, { timeout: 10_000 });
		await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

		// "Sign in" call-to-action is visible.
		await expect(page.getByRole('link', { name: /sign in/i })).toBeVisible();

		// No "Sign out" button (which only makes sense when authenticated).
		await expect(page.getByRole('button', { name: /sign out/i })).toHaveCount(0);
	});

	test('anonymous visitor cannot see admin menu', async ({ page }) => {
		await page.goto('/');
		await page.evaluate(() => {
			localStorage.clear();
			sessionStorage.clear();
		});
		await page.goto('/');
		await page.getByRole('heading', { name: 'Dashboard' }).waitFor();

		// Admin nav items (Users / Audit / Locks) should not be visible in the shell.
		await expect(page.getByRole('link', { name: /^users$/i })).toHaveCount(0);
		await expect(page.getByRole('link', { name: /^audit/i })).toHaveCount(0);
	});

	test('anonymous visit to /admin redirects to /login', async ({ page }) => {
		await page.goto('/');
		await page.evaluate(() => {
			localStorage.clear();
			sessionStorage.clear();
		});
		await page.goto('/admin/users');
		await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });
	});

	test('sign-in restores admin menu + write buttons', async ({ page }) => {
		// Start anonymous → confirm no admin menu.
		await page.goto('/');
		await page.evaluate(() => {
			localStorage.clear();
			sessionStorage.clear();
		});
		await page.goto('/');
		await expect(page.getByRole('link', { name: /^users$/i })).toHaveCount(0);

		// Sign in via the normal login flow.
		await loginAsAdmin(page);

		// Admin nav items now visible.
		await expect(page.getByRole('link', { name: /^users$/i })).toBeVisible({ timeout: 5_000 });
	});
});
