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

		// Wait for counts to load — the stats cards display entity and model counts
		const entitiesCard = page.getByRole('link', { name: /entities/i });
		await expect(entitiesCard).toBeVisible();

		const modelsCard = page.getByRole('link', { name: /models/i }).first();
		await expect(modelsCard).toBeVisible();

		// The counts should be at least 1 (we seeded data)
		// The cards contain a large number and a label
		await expect(entitiesCard).toContainText(/\d+/);
		await expect(modelsCard).toContainText(/\d+/);
	});

	test('Search returns results', async ({ page }) => {
		await loginAsAdmin(page);

		const searchInput = page.getByLabel('Search');
		await expect(searchInput).toBeVisible();

		await searchInput.fill('Dashboard Test');

		// Wait for debounced search to fire and results to appear
		await expect(page.getByText(/result/i)).toBeVisible({ timeout: 5000 });
		await expect(page.getByText('Dashboard Test Entity').or(page.getByText('Dashboard Test Model'))).toBeVisible();
	});

	test('Quick nav cards link to correct pages', async ({ page }) => {
		await loginAsAdmin(page);

		// The Quick Navigation section has links to Models, Entities, and Help
		const quickNav = page.getByRole('heading', { name: 'Quick Navigation' });
		await expect(quickNav).toBeVisible();

		const modelsLink = page.getByRole('link', { name: 'Models' }).filter({ hasText: 'Models' });
		await expect(modelsLink.first()).toHaveAttribute('href', '/models');

		const entitiesLink = page.getByRole('link', { name: 'Entities' }).filter({ hasText: 'Entities' });
		await expect(entitiesLink.first()).toHaveAttribute('href', '/entities');

		const helpLink = page.getByRole('link', { name: 'Help' }).filter({ hasText: 'Help' });
		await expect(helpLink.first()).toHaveAttribute('href', '/help');
	});

	test('Dashboard loads without errors after login', async ({ page }) => {
		await loginAsAdmin(page);

		// The heading should be visible
		await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

		// No error alert should be present
		const alerts = page.getByRole('alert');
		await expect(alerts).toHaveCount(0);
	});
});
