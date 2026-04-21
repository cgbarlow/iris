import { test, expect } from '@playwright/test';
import { seedAdmin, getAuthToken, loginAsAdmin, createEntity, createModel } from './fixtures';

test.describe('Dashboard', () => {
	test.beforeAll(async () => {
		await seedAdmin();
		const token = await getAuthToken();

		// Seed some data so counts are non-zero
		await createEntity(undefined, token, {
			name: 'Dashboard Test Entity',
			entity_type: 'system',
			description: 'Entity created for dashboard tests',
		});
		await createModel(undefined, token, {
			name: 'Dashboard Test Model',
			model_type: 'component',
			description: 'Model created for dashboard tests',
		});
	});

	test('Dashboard shows entity and model counts', async ({ page }) => {
		await loginAsAdmin(page);

		const main = page.locator('main');

		// Wait for counts to load — the stats cards display entity and model counts
		const entitiesCard = main.getByRole('link', { name: /entities/i }).first();
		await expect(entitiesCard).toBeVisible({ timeout: 15_000 });

		const modelsCard = main.getByRole('link', { name: /models/i }).first();
		await expect(modelsCard).toBeVisible({ timeout: 10_000 });

		// The counts should be at least 1 (we seeded data)
		// The cards contain a large number and a label
		await expect(entitiesCard).toContainText(/\d+/);
		await expect(modelsCard).toContainText(/\d+/);
	});

	test('Search returns results', async ({ page }) => {
		await loginAsAdmin(page);

		const searchInput = page.getByLabel('Search');
		await expect(searchInput).toBeVisible({ timeout: 15_000 });

		await searchInput.fill('Dashboard Test');

		// Wait for debounced search to fire and results to appear
		await expect(page.getByText(/result/i)).toBeVisible({ timeout: 5000 });
		await expect(page.getByText('Dashboard Test Entity').first()).toBeVisible();
	});

	// The old dashboard "Quick Navigation" section (Models / Entities / Help)
	// is no longer part of the UI — replaced by the knowledge graph + counts
	// panel in v4.x. Test removed; the left-sidebar navigation is covered by
	// navigation.spec.ts.

	test('Dashboard loads without errors after login', async ({ page }) => {
		await loginAsAdmin(page);

		// The heading should be visible
		await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

		// Wait for dashboard data to finish loading before checking for errors
		await expect(page.getByText('Loading dashboard...')).not.toBeVisible({ timeout: 15_000 });

		// No error alert should be present
		const alerts = page.getByRole('alert');
		await expect(alerts).toHaveCount(0);
	});
});
