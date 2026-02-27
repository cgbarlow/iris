import { test, expect } from '@playwright/test';
import { seedAdmin, loginAsAdmin } from './fixtures';

test.describe('Error Handling', () => {
	test.beforeAll(async () => {
		await seedAdmin();
	});

	test('Non-existent model ID shows error', async ({ page }) => {
		await loginAsAdmin(page);

		// Navigate to a model with a fake UUID
		await page.goto('/models/00000000-0000-0000-0000-000000000000');

		// Should display an error message
		const alert = page.getByRole('alert');
		await expect(alert).toBeVisible({ timeout: 10_000 });
		await expect(alert).toContainText(/not found|failed/i);
	});

	test('Non-existent entity ID shows error', async ({ page }) => {
		await loginAsAdmin(page);

		// Navigate to an entity with a fake UUID
		await page.goto('/entities/00000000-0000-0000-0000-000000000000');

		// Should display an error message
		const alert = page.getByRole('alert');
		await expect(alert).toBeVisible({ timeout: 10_000 });
		await expect(alert).toContainText(/not found|failed/i);
	});

	test('Search with no results shows message', async ({ page }) => {
		await loginAsAdmin(page);

		// Type a query that will not match anything
		const searchInput = page.getByLabel('Search');
		await searchInput.fill('zzz_no_match_xyz_999');

		// Wait for the debounced search to fire
		await page.waitForTimeout(500);

		// Should show "No results found."
		await expect(page.getByText('No results found.')).toBeVisible({ timeout: 5000 });
	});
});
