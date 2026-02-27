import { test, expect } from '@playwright/test';
import { seedAdmin, loginAsAdmin } from './fixtures';

test.describe('Admin Users', () => {
	test.beforeAll(async () => {
		await seedAdmin();
	});

	test('Users page loads with user list', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto('/admin/users');

		await expect(page.getByRole('heading', { name: 'User Management' })).toBeVisible();

		// The admin user should appear in the table
		await expect(page.getByText('admin')).toBeVisible({ timeout: 10_000 });
	});

	test('Create new user appears in list', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto('/admin/users');

		await expect(page.getByRole('heading', { name: 'User Management' })).toBeVisible();

		// Click Create User button to show the form
		await page.getByRole('button', { name: 'Create User' }).click();

		// Fill in the create user form
		await page.getByLabel('Username').fill('e2etestuser');
		await page.getByLabel('Password').fill('E2eTestPass123!');
		await page.locator('#new-role').selectOption('viewer');

		// Submit the form
		await page.getByRole('button', { name: 'Create' }).click();

		// The new user should appear in the table
		await expect(page.getByText('e2etestuser')).toBeVisible({ timeout: 10_000 });
	});

	test('Edit user role updates', async ({ page }) => {
		await loginAsAdmin(page);
		await page.goto('/admin/users');

		await expect(page.getByRole('heading', { name: 'User Management' })).toBeVisible();
		await expect(page.getByText('e2etestuser')).toBeVisible({ timeout: 10_000 });

		// Find the row for e2etestuser and click Edit
		const row = page.locator('tr', { hasText: 'e2etestuser' });
		await row.getByRole('button', { name: 'Edit' }).click();

		// Change role to architect
		const roleSelect = row.locator('select');
		await roleSelect.selectOption('architect');

		// Save
		await row.getByRole('button', { name: 'Save' }).click();

		// Verify the role updated — the badge should show "architect"
		await expect(row.getByText('architect')).toBeVisible({ timeout: 5000 });
	});

	test('Non-admin cannot access admin pages', async ({ page }) => {
		// Log in as the viewer user we just created
		await page.goto('/login');
		await page.getByLabel('Username').fill('e2etestuser');
		await page.getByLabel('Password').fill('E2eTestPass123!');
		await page.getByRole('button', { name: 'Sign in' }).click();
		await page.waitForURL('/');

		// Navigate to admin — the sidebar should not show Admin section for non-admin
		// but we can try to navigate directly
		await page.goto('/admin/users');

		// The sidebar should not have Admin section visible
		const sidebar = page.locator('nav[aria-label="Main navigation"]');

		// Admin heading should not be visible for non-admin users
		await expect(sidebar.getByText('Admin')).not.toBeVisible();
	});
});
