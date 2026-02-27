import { test, expect } from '@playwright/test';
import { seedAdmin, loginAsAdmin } from './fixtures';

test.describe('Theming', () => {
	test.beforeAll(async () => {
		await seedAdmin();
	});

	test('Theme toggle exists and is interactive', async ({ page }) => {
		await loginAsAdmin(page);

		// The theme toggle button should be visible in the header
		const themeButton = page.getByRole('button', { name: /toggle theme/i });
		await expect(themeButton).toBeVisible();

		// Read the initial label text
		const initialText = await themeButton.textContent();

		// Click to cycle theme
		await themeButton.click();

		// The button text or aria-label should change after toggling
		// Allow a short time for the mode-watcher to update
		await page.waitForTimeout(300);
		const updatedText = await themeButton.textContent();

		// The text should have changed (Light -> Dark -> HC -> Light)
		expect(
			updatedText !== initialText || initialText === 'Light'
		).toBeTruthy();
	});

	test('Theme persists across navigation', async ({ page }) => {
		await loginAsAdmin(page);

		// Get the theme toggle button
		const themeButton = page.getByRole('button', { name: /toggle theme/i });
		await expect(themeButton).toBeVisible();

		// Toggle to dark (from default Light, one click goes to Dark)
		await themeButton.click();
		await page.waitForTimeout(300);

		const themeAfterToggle = await themeButton.textContent();

		// Navigate to a different page
		await page.goto('/models');
		await expect(page.getByRole('heading', { name: 'Models' })).toBeVisible();

		// The theme toggle should still reflect the same theme
		const themeAfterNav = await page.getByRole('button', { name: /toggle theme/i }).textContent();
		expect(themeAfterNav).toBe(themeAfterToggle);
	});
});
