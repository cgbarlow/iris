/**
 * System notification banner end-to-end test (ADR-124 / SPEC-124-A).
 *
 * Admin sets a banner message on /admin/settings; an anonymous browser
 * context sees it on the dashboard. Dismiss hides it locally; an admin-
 * posted *different* message re-appears (hash-keyed dismissal).
 */

import { expect, test } from '@playwright/test';
import { seedAdmin, loginAsAdmin } from './fixtures';

const BANNER_1 = 'UAT notice — AI provider being worked on';
const BANNER_2 = 'UAT notice — AI provider restored';

test.describe('System notification banner (ADR-124)', () => {
	test.describe.configure({ timeout: 120_000 });

	test.beforeAll(async ({ baseURL }) => {
		await seedAdmin(baseURL);
	});

	test.afterEach(async ({ page }) => {
		// Leave UAT-like state clean for the next test — clear the banner.
		try {
			await loginAsAdmin(page);
			await page.goto('/admin/settings');
			await page.getByLabel('Banner message').fill('');
			await page.getByRole('button', { name: 'Save Settings' }).click();
			await page.getByText(/saved successfully/i).waitFor({ timeout: 5_000 });
		} catch { /* best-effort cleanup */ }
	});

	test('admin sets banner → anonymous visitor sees it; dismiss hides it; new message re-appears', async ({ browser }) => {
		// --- Admin side: set the banner ---
		const adminCtx = await browser.newContext();
		const adminPage = await adminCtx.newPage();
		await loginAsAdmin(adminPage);
		await adminPage.goto('/admin/settings');
		await adminPage.getByLabel('Banner message').fill(BANNER_1);
		await adminPage.getByRole('button', { name: 'Save Settings' }).click();
		await adminPage.getByText(/saved successfully/i).waitFor({ timeout: 5_000 });

		// --- Anonymous side: banner visible immediately on load ---
		const anonCtx = await browser.newContext();
		const anonPage = await anonCtx.newPage();
		await anonPage.goto('/');
		await expect(anonPage.getByTestId('system-banner')).toContainText(BANNER_1, {
			timeout: 10_000,
		});

		// Dismiss — banner hidden for this tab ...
		await anonPage.getByRole('button', { name: 'Dismiss notification' }).click();
		await expect(anonPage.getByTestId('system-banner')).toHaveCount(0);

		// ... and stays dismissed across a reload (localStorage persists).
		await anonPage.reload();
		await anonPage.getByRole('heading', { name: 'Dashboard' }).waitFor();
		await expect(anonPage.getByTestId('system-banner')).toHaveCount(0);

		// --- Admin changes message — new hash, dismiss no longer applies ---
		await adminPage.goto('/admin/settings');
		await adminPage.getByLabel('Banner message').fill(BANNER_2);
		await adminPage.getByRole('button', { name: 'Save Settings' }).click();
		await adminPage.getByText(/saved successfully/i).waitFor({ timeout: 5_000 });

		// Reload anon tab; new message shows because its hash differs from
		// the dismissed one.
		await anonPage.reload();
		await expect(anonPage.getByTestId('system-banner')).toContainText(BANNER_2, {
			timeout: 10_000,
		});

		await anonCtx.close();
		await adminCtx.close();
	});

	test('public GET /api/notifications/banner is anonymous-readable', async ({ request }) => {
		const resp = await request.get('/api/notifications/banner');
		expect(resp.status()).toBe(200);
		const body = await resp.json();
		expect(body).toHaveProperty('message');
	});
});
