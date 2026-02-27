import { test, expect } from '@playwright/test';
import { seedAdmin, getAuthToken, loginAsAdmin, createEntity } from './fixtures';

test.describe('Admin Audit Log', () => {
	test.beforeAll(async () => {
		await seedAdmin();
		const token = await getAuthToken();

		// Create an entity to generate audit entries
		await createEntity(undefined, token, {
			name: 'Audit Test Entity',
			entity_type: 'system',
			description: 'Entity created to produce audit log entries',
		});
	});

	test('Audit log loads with entries', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto('/admin/audit');

		await expect(page.getByRole('heading', { name: 'Audit Log' })).toBeVisible();

		// Wait for table to load — should show at least one entry
		await expect(page.locator('table tbody tr').first()).toBeVisible({ timeout: 10_000 });
	});

	test('Filter by action narrows results', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto('/admin/audit');

		await expect(page.getByRole('heading', { name: 'Audit Log' })).toBeVisible();

		// Wait for the table to be populated
		await expect(page.locator('table tbody tr').first()).toBeVisible({ timeout: 10_000 });

		// Type a filter into the Action field
		const actionInput = page.getByLabel('Action');
		await actionInput.fill('POST');

		// Click Apply Filters
		await page.getByRole('button', { name: 'Apply Filters' }).click();

		// Wait for filtered results — entries should contain POST
		await expect(page.locator('table tbody tr').first()).toBeVisible({ timeout: 10_000 });

		// All visible action cells should contain POST
		const actionCells = page.locator('table tbody tr td:nth-child(4)');
		const count = await actionCells.count();
		if (count > 0) {
			for (let i = 0; i < count; i++) {
				await expect(actionCells.nth(i)).toContainText('POST');
			}
		}
	});

	test('Chain verification shows valid', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto('/admin/audit');

		// The verification badge should appear — "Chain Valid" with entry count
		await expect(page.getByText(/Chain Valid/)).toBeVisible({ timeout: 10_000 });
		await expect(page.getByText(/\d+ entries/)).toBeVisible();
	});

	test('Expandable row shows detail', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto('/admin/audit');

		// Wait for table to load
		await expect(page.locator('table tbody tr').first()).toBeVisible({ timeout: 10_000 });

		// Find a row with a "Show" button (detail available)
		const showButton = page.getByRole('button', { name: 'Show' }).first();

		// If there is a Show button, click it and verify expanded content
		if (await showButton.isVisible()) {
			await showButton.click();

			// A <pre> element with detail content should appear
			await expect(page.locator('pre').first()).toBeVisible();

			// The button should now say "Hide"
			await expect(page.getByRole('button', { name: 'Hide' }).first()).toBeVisible();
		}
	});
});
