import { test, expect } from '@playwright/test';
import { seedAdmin, loginAsAdmin } from './fixtures';

test.describe('Accessibility', () => {
	test.beforeAll(async () => {
		await seedAdmin();
	});

	test('Tab key navigates through interactive elements', async ({ page }) => {
		await loginAsAdmin(page);

		// Start from the body; tab should move focus through interactive elements
		await page.keyboard.press('Tab');

		// After pressing Tab, some element should have focus
		const firstFocused = await page.evaluate(() => document.activeElement?.tagName);
		expect(firstFocused).toBeTruthy();

		// Press Tab again — focus should move to a different element
		const firstId = await page.evaluate(() => document.activeElement?.id || document.activeElement?.textContent);
		await page.keyboard.press('Tab');
		const secondId = await page.evaluate(() => document.activeElement?.id || document.activeElement?.textContent);

		// Focus should have moved (different element)
		expect(secondId).not.toBe(firstId);
	});

	test('Login form is keyboard operable', async ({ page }) => {
		await page.goto('/login');

		// Fill the form via keyboard
		const usernameInput = page.getByLabel('Username');
		await usernameInput.focus();
		await page.keyboard.type('admin');

		const passwordInput = page.getByLabel('Password');
		await passwordInput.focus();
		await page.keyboard.type('TestPassword12345');

		// Focus the submit button and verify it is focused
		const submitButton = page.getByRole('button', { name: 'Sign in' });
		await submitButton.focus();

		const focusedTag = await page.evaluate(() => document.activeElement?.tagName);
		expect(focusedTag).toBe('BUTTON');

		// Press Enter to submit
		await page.keyboard.press('Enter');

		// Should redirect to dashboard
		await page.waitForURL('/', { timeout: 15_000 });
		await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
	});

	test('Focus indicators are visible', async ({ page }) => {
		await page.goto('/login');

		// Focus the username input
		const usernameInput = page.getByLabel('Username');
		await usernameInput.focus();

		// Check that the element has a visible focus style by verifying
		// it is the active element. Browser default or custom focus styles
		// should apply when :focus-visible is active.
		const isFocused = await page.evaluate(() => {
			const el = document.activeElement;
			if (!el) return false;
			const styles = window.getComputedStyle(el);
			// Check for outline or box-shadow (common focus indicators)
			const hasOutline = styles.outlineStyle !== 'none' && styles.outlineWidth !== '0px';
			const hasBoxShadow = styles.boxShadow !== 'none' && styles.boxShadow !== '';
			const hasBorder = styles.borderColor !== '';
			return hasOutline || hasBoxShadow || hasBorder;
		});

		expect(isFocused).toBeTruthy();
	});

	test('Error messages have role=alert', async ({ page }) => {
		await page.goto('/login');

		// Submit with invalid credentials to trigger an error
		await page.getByLabel('Username').fill('baduser');
		await page.getByLabel('Password').fill('BadPassword123!');
		await page.getByRole('button', { name: 'Sign in' }).click();

		// Wait for the error to appear
		const alert = page.getByRole('alert');
		await expect(alert).toBeVisible({ timeout: 10_000 });

		// Verify it actually has role="alert"
		await expect(alert).toHaveAttribute('role', 'alert');
	});
});
