import { test, expect } from '@playwright/test';
import { seedAdmin, loginAsAdmin } from './fixtures';

test.describe('Theming', () => {
	test.beforeAll(async () => {
		await seedAdmin();
	});

	test('Settings page has theme radio buttons', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto('/settings');

		await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();

		// All four theme options should be visible
		await expect(page.getByLabel('System')).toBeVisible();
		await expect(page.getByLabel('Light')).toBeVisible();
		await expect(page.getByLabel('Dark')).toBeVisible();
		await expect(page.getByLabel('High Contrast')).toBeVisible();
	});

	test('Theme can be changed via Settings page', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto('/settings');

		await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();

		// Select Dark theme
		await page.getByLabel('Dark').check();
		await page.waitForTimeout(300);

		// The html element should have the dark class
		const hasDark = await page.evaluate(() =>
			document.documentElement.classList.contains('dark'),
		);
		expect(hasDark).toBeTruthy();

		// Select Light theme
		await page.getByLabel('Light').check();
		await page.waitForTimeout(300);

		const hasDarkAfterLight = await page.evaluate(() =>
			document.documentElement.classList.contains('dark'),
		);
		expect(hasDarkAfterLight).toBeFalsy();
	});

	test('Theme persists across navigation', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto('/settings');

		await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();

		// Select Dark theme
		await page.getByLabel('Dark').check();
		await page.waitForTimeout(300);

		// Navigate to a different page
		await page.goto('/models');
		await expect(page.getByRole('heading', { name: 'Models' })).toBeVisible();

		// Navigate back to Settings — Dark should still be selected
		await page.goto('/settings');
		await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();

		const darkChecked = await page.getByLabel('Dark').isChecked();
		expect(darkChecked).toBeTruthy();
	});
});
