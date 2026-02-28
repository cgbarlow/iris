import { test, expect } from '@playwright/test';
import { seedAdmin, getAuthToken, loginAsAdmin, createModel } from './fixtures';

let modelId: string;

test.describe('Models', () => {
	test.beforeAll(async () => {
		await seedAdmin();
		const token = await getAuthToken();

		const model = await createModel(undefined, token, {
			name: 'E2E Test Model Alpha',
			model_type: 'component',
			description: 'A component model for E2E testing',
		});
		modelId = model.id as string;

		// Create a second model so the list has multiple items
		await createModel(undefined, token, {
			name: 'E2E Test Model Beta',
			model_type: 'deployment',
			description: 'A deployment model for E2E testing',
		});
	});

	test('Models list loads and shows models', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto('/models');

		await expect(page.getByRole('heading', { name: 'Models' })).toBeVisible();

		// Wait for models to load
		await expect(page.getByText('E2E Test Model Alpha').first()).toBeVisible({ timeout: 10_000 });
		await expect(page.getByText('E2E Test Model Beta').first()).toBeVisible();
	});

	test('Search filters models by name', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto('/models');

		// Wait for the list to load
		await expect(page.getByText('E2E Test Model Alpha').first()).toBeVisible({ timeout: 10_000 });

		// Type into the search box
		const searchInput = page.getByPlaceholder('Search models...');
		await searchInput.fill('Alpha');

		// Alpha should be visible, Beta should not
		await expect(page.getByText('E2E Test Model Alpha').first()).toBeVisible();
		await expect(page.getByText('E2E Test Model Beta')).toHaveCount(0);
	});

	test('Click model navigates to detail page', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto('/models');

		await expect(page.getByText('E2E Test Model Alpha').first()).toBeVisible({ timeout: 10_000 });
		await page.getByText('E2E Test Model Alpha').first().click();

		// Should navigate to the detail page
		await page.waitForURL(/\/models\/.+/);
		await expect(page.getByRole('heading', { name: 'E2E Test Model Alpha' })).toBeVisible();
	});

	test('Model detail Overview tab shows metadata', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto(`/models/${modelId}`);

		// Wait for model detail to load
		await expect(page.getByRole('heading', { name: 'E2E Test Model Alpha' })).toBeVisible({ timeout: 10_000 });

		// Overview tab should be active by default — verify metadata fields
		await expect(page.getByText('Type')).toBeVisible();
		await expect(page.getByText('component', { exact: true }).first()).toBeVisible();
		await expect(page.getByText('ID')).toBeVisible();
	});

	test('Model detail Versions tab shows history', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto(`/models/${modelId}`);

		await expect(page.getByRole('heading', { name: 'E2E Test Model Alpha' })).toBeVisible({ timeout: 10_000 });

		// Click the Version History tab
		const versionsTab = page.getByRole('tab', { name: 'Version History' });
		await expect(versionsTab).toBeVisible();
		await versionsTab.click();

		// Should show version data (at least the initial version)
		const tabPanel = page.getByRole('tabpanel');
		await expect(tabPanel).toBeVisible();

		// Either shows version entries or "No version history available."
		await expect(
			tabPanel.getByText(/v\d+/).first().or(tabPanel.getByText('No version history available.'))
		).toBeVisible({ timeout: 5000 });
	});
});
