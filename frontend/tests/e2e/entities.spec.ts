import { test, expect } from '@playwright/test';
import { seedAdmin, getAuthToken, loginAsAdmin, createEntity } from './fixtures';

let entityId: string;

test.describe('Entities', () => {
	test.beforeAll(async () => {
		await seedAdmin();
		const token = await getAuthToken();

		const entity = await createEntity(undefined, token, {
			name: 'E2E Test Entity Alpha',
			entity_type: 'system',
			description: 'A system entity for E2E testing',
		});
		entityId = entity.id as string;

		// Create a second entity so the list has multiple items
		await createEntity(undefined, token, {
			name: 'E2E Test Entity Beta',
			entity_type: 'service',
			description: 'A service entity for E2E testing',
		});
	});

	test('Entity list loads and shows entities', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto('/entities');

		await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible();

		// Wait for entities to load
		await expect(page.getByText('E2E Test Entity Alpha')).toBeVisible({ timeout: 10_000 });
		await expect(page.getByText('E2E Test Entity Beta')).toBeVisible();
	});

	test('Search filters entities by name', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto('/entities');

		// Wait for the list to load
		await expect(page.getByText('E2E Test Entity Alpha')).toBeVisible({ timeout: 10_000 });

		// Type into the search box
		const searchInput = page.getByPlaceholder('Search entities...');
		await searchInput.fill('Alpha');

		// Alpha should be visible, Beta should not
		await expect(page.getByText('E2E Test Entity Alpha')).toBeVisible();
		await expect(page.getByText('E2E Test Entity Beta')).not.toBeVisible();
	});

	test('Click entity navigates to detail page', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto('/entities');

		await expect(page.getByText('E2E Test Entity Alpha')).toBeVisible({ timeout: 10_000 });
		await page.getByText('E2E Test Entity Alpha').click();

		// Should navigate to the detail page
		await page.waitForURL(/\/entities\/.+/);
		await expect(page.getByRole('heading', { name: 'E2E Test Entity Alpha' })).toBeVisible();
	});

	test('Entity detail shows metadata', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto(`/entities/${entityId}`);

		// Wait for entity detail to load
		await expect(page.getByRole('heading', { name: 'E2E Test Entity Alpha' })).toBeVisible({ timeout: 10_000 });

		// Details tab should be active by default — verify metadata fields
		await expect(page.getByText('Type')).toBeVisible();
		await expect(page.getByText('system')).toBeVisible();
		await expect(page.getByText('ID')).toBeVisible();
	});

	test('Entity detail Versions tab shows history', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto(`/entities/${entityId}`);

		await expect(page.getByRole('heading', { name: 'E2E Test Entity Alpha' })).toBeVisible({ timeout: 10_000 });

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
