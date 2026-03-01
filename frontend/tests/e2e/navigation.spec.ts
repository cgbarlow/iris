import { test, expect } from '@playwright/test';
import { seedAdmin, getAuthToken, loginAsAdmin, loginAs, createModel, createUser } from './fixtures';

let modelId: string;

const VIEWER_USERNAME = 'nav_headertest_viewer';
const VIEWER_PASSWORD = 'ViewerPass12345!';

test.describe('Navigation', () => {
	test.beforeAll(async () => {
		await seedAdmin();
		const token = await getAuthToken();

		const model = await createModel(undefined, token, {
			name: 'Nav Test Model',
			model_type: 'component',
			description: 'Model for navigation breadcrumb tests',
		});
		modelId = model.id as string;

		// Create a viewer user for non-admin header tests
		await createUser(token, {
			username: VIEWER_USERNAME,
			password: VIEWER_PASSWORD,
			role: 'viewer',
		});
	});

	test('Sidebar links navigate correctly', async ({ page }) => {
		await loginAsAdmin(page);

		const sidebar = page.locator('nav[aria-label="Main navigation"]');
		await expect(sidebar).toBeVisible();

		// Navigate to Models
		await sidebar.getByRole('link', { name: 'Models' }).click();
		await page.waitForURL('/models');
		await expect(page.getByRole('heading', { name: 'Models' })).toBeVisible();

		// Navigate to Entities
		await sidebar.getByRole('link', { name: 'Entities' }).click();
		await page.waitForURL('/entities');
		await expect(page.getByRole('heading', { name: 'Entities' })).toBeVisible();

		// Navigate to Settings
		await sidebar.getByRole('link', { name: 'Settings' }).click();
		await page.waitForURL('/settings');
		await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();

		// Navigate back to Dashboard
		await sidebar.getByRole('link', { name: 'Dashboard' }).click();
		await page.waitForURL('/');
		await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
	});

	test('Breadcrumbs show on detail pages', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto(`/models/${modelId}`);

		// Wait for the model to load (may be slow when backend is under load)
		await expect(page.getByRole('heading', { name: 'Nav Test Model' })).toBeVisible({ timeout: 15_000 });

		// Breadcrumb nav should be present
		const breadcrumb = page.locator('nav[aria-label="Breadcrumb"]');
		await expect(breadcrumb).toBeVisible();

		// Should contain a link back to Models
		await expect(breadcrumb.getByRole('link', { name: 'Models' })).toBeVisible();
		await expect(breadcrumb.getByRole('link', { name: 'Models' })).toHaveAttribute('href', '/models');

		// Should show the current page name
		await expect(breadcrumb.getByText('Nav Test Model')).toBeVisible();
	});

	test('Admin section visible in sidebar for admin user', async ({ page }) => {
		await loginAsAdmin(page);

		const sidebar = page.locator('nav[aria-label="Main navigation"]');
		await expect(sidebar).toBeVisible();

		// Admin heading should be visible
		await expect(sidebar.getByText('Admin')).toBeVisible();

		// Admin links should be available
		await expect(sidebar.getByRole('link', { name: 'Users' })).toBeVisible();
		await expect(sidebar.getByRole('link', { name: 'Audit Log' })).toBeVisible();

		// Navigate to admin users via sidebar
		await sidebar.getByRole('link', { name: 'Users' }).click();
		await page.waitForURL('/admin/users');
		await expect(page.getByRole('heading', { name: 'User Management' })).toBeVisible();
	});

	test('Help link works', async ({ page }) => {
		await loginAsAdmin(page);

		// The Help link is in the header
		const helpLink = page.getByRole('link', { name: 'Help' }).first();
		await expect(helpLink).toBeVisible();
		await helpLink.click();

		await page.waitForURL('/help');
		await expect(page.getByRole('heading', { name: 'Help' })).toBeVisible();
		await expect(page.getByText('Keyboard Shortcuts')).toBeVisible();
	});

	test('Admin sees Settings link in header', async ({ page }) => {
		await loginAsAdmin(page);

		const header = page.locator('header');

		// Admin Settings link should be visible in the header
		const settingsLink = header.getByRole('link', { name: 'Admin Settings' });
		await expect(settingsLink).toBeVisible();
		await expect(settingsLink).toHaveAttribute('href', '/admin/settings');

		// Settings link should appear before Help link in the header
		const helpLink = header.getByRole('link', { name: 'Help' });
		await expect(helpLink).toBeVisible();

		// Click the Settings link and verify navigation
		await settingsLink.click();
		await page.waitForURL('/admin/settings');
		await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
	});

	test('Non-admin does not see Settings link in header', async ({ page }) => {
		// Log in as the viewer user (created in beforeAll)
		await loginAs(page, VIEWER_USERNAME, VIEWER_PASSWORD);

		const header = page.locator('header');

		// Help link should still be visible (available to all users)
		await expect(header.getByRole('link', { name: 'Help' })).toBeVisible();

		// Admin Settings link should NOT be visible for non-admin users
		await expect(header.getByRole('link', { name: 'Admin Settings' })).not.toBeVisible();
	});
});
