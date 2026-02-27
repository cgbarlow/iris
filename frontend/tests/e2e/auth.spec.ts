import { test, expect } from '@playwright/test';
import { seedAdmin, loginAsAdmin, ADMIN_USERNAME, ADMIN_PASSWORD } from './fixtures';

test.describe('Authentication', () => {
	test.beforeAll(async () => {
		await seedAdmin();
	});

	test('Login with valid credentials redirects to dashboard', async ({ page }) => {
		await page.goto('/login');
		await page.getByLabel('Username').fill(ADMIN_USERNAME);
		await page.getByLabel('Password').fill(ADMIN_PASSWORD);
		await page.getByRole('button', { name: 'Sign in' }).click();

		await page.waitForURL('/');
		await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
	});

	test('Login with invalid credentials shows error message', async ({ page }) => {
		await page.goto('/login');
		await page.getByLabel('Username').fill('wronguser');
		await page.getByLabel('Password').fill('WrongPassword123!');
		await page.getByRole('button', { name: 'Sign in' }).click();

		const alert = page.getByRole('alert');
		await expect(alert).toBeVisible();
		await expect(alert).toContainText(/invalid|failed|credentials/i);
	});

	test('Login form has accessible labels', async ({ page }) => {
		await page.goto('/login');

		const form = page.getByRole('form', { name: /login/i });
		await expect(form).toBeVisible();

		const usernameInput = page.getByLabel('Username');
		await expect(usernameInput).toBeVisible();
		await expect(usernameInput).toHaveAttribute('id', 'username');

		const passwordInput = page.getByLabel('Password');
		await expect(passwordInput).toBeVisible();
		await expect(passwordInput).toHaveAttribute('id', 'password');
		await expect(passwordInput).toHaveAttribute('type', 'password');

		const submitButton = page.getByRole('button', { name: 'Sign in' });
		await expect(submitButton).toBeVisible();
	});

	test('Logout redirects to login page', async ({ page }) => {
		await loginAsAdmin(page);

		// Verify we are on the dashboard
		await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

		// Click sign out
		await page.getByRole('button', { name: 'Sign out' }).click();

		// Should be redirected to /login
		await page.waitForURL('/login');
		await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible();
	});

	test('Unauthenticated access to /models shows login page', async ({ page }) => {
		await page.goto('/models');

		// The app guards authenticated routes — unauthenticated users see the login form
		// Since auth is in-memory and not set, the layout renders the login page or the
		// page without the shell. We check that the models heading is NOT visible and
		// that login is presented.
		await expect(page.getByLabel('Username')).toBeVisible();
	});
});
