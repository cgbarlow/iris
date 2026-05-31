import { test, expect } from '@playwright/test';

// Desktop regression guard for the mobile-responsive AppShell change (ADR-229).
// Runs under the default `e2e` project (1280px viewport). On desktop the
// persistent inline sidebar must still render (NOT the mobile drawer), so the
// drawer work can't have regressed the desktop shell. Anonymous-safe (ADR-123)
// so it doesn't depend on seedAdmin/login.

test('desktop renders the persistent inline sidebar, not the drawer', async ({ page }) => {
	await page.goto('/');

	// The inline sidebar is a `navigation` landmark and is visible by default.
	const nav = page.getByRole('navigation', { name: 'Main navigation' });
	await expect(nav).toBeVisible();
	await expect(nav.getByRole('link', { name: 'Collections', exact: true })).toBeVisible();
	await expect(nav.getByRole('link', { name: 'Elements', exact: true })).toBeVisible();

	// It is NOT the mobile Dialog drawer.
	await expect(page.getByRole('dialog', { name: 'Main navigation' })).toHaveCount(0);

	// The hamburger collapses the persistent sidebar (original desktop behaviour).
	await page.getByRole('button', { name: 'Close navigation' }).click();
	await expect(nav).toHaveCount(0);
	await page.getByRole('button', { name: 'Open navigation' }).click();
	await expect(page.getByRole('navigation', { name: 'Main navigation' })).toBeVisible();
});
