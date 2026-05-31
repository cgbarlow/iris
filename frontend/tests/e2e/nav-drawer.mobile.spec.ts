import { test, expect } from '@playwright/test';

// Phase 1 of the mobile-responsive rollout (ADR-229 / SPEC-229-A).
// Runs under the `mobile` Playwright project (Pixel 5, 393px wide). The app
// shell renders for anonymous visitors (ADR-123), so these need no seeding.
//
// On mobile the persistent desktop sidebar (a `nav` landmark) is replaced by a
// bits-ui Dialog drawer (role `dialog`, labelled "Main navigation"). Assertions
// target the dialog so they can't collide with same-named dashboard content.

test.beforeEach(async ({ page }) => {
	await page.goto('/');
	// Wait for the viewport store to reconcile to mobile after mount — the
	// hamburger advertises "Open navigation" while the drawer is closed.
	await expect(page.getByRole('button', { name: 'Open navigation' })).toBeVisible();
});

test('desktop sidebar nav is not rendered on a mobile viewport', async ({ page }) => {
	// Neither the desktop sidebar nor the (closed) drawer expose a nav landmark.
	await expect(page.getByRole('navigation', { name: 'Main navigation' })).toHaveCount(0);
	await expect(page.getByRole('dialog', { name: 'Main navigation' })).toHaveCount(0);
});

test('hamburger opens the drawer and reveals the nav', async ({ page }) => {
	await page.getByRole('button', { name: 'Open navigation' }).click();

	const drawer = page.getByRole('dialog', { name: 'Main navigation' });
	await expect(drawer).toBeVisible();
	await expect(drawer.getByRole('link', { name: 'Collections', exact: true })).toBeVisible();
	await expect(drawer.getByRole('link', { name: 'Elements', exact: true })).toBeVisible();
	// Background scroll is locked while the drawer is open (bits-ui sets this).
	await expect(page.locator('body')).toHaveCSS('overflow', 'hidden');
});

test('Escape closes the drawer and restores focus to the hamburger', async ({ page }) => {
	const hamburger = page.getByRole('button', { name: 'Open navigation' });
	await hamburger.click();
	const drawer = page.getByRole('dialog', { name: 'Main navigation' });
	await expect(drawer).toBeVisible();

	await page.keyboard.press('Escape');
	await expect(drawer).toHaveCount(0);
	await expect(hamburger).toBeFocused();
});

test('clicking the backdrop closes the drawer', async ({ page }) => {
	await page.getByRole('button', { name: 'Open navigation' }).click();
	const drawer = page.getByRole('dialog', { name: 'Main navigation' });
	await expect(drawer).toBeVisible();

	// Click the overlay clear of the 18rem (≈288px) drawer. Position is relative
	// to the full-bleed overlay's top-left, so x≈370 is past the drawer's edge.
	const overlay = page.locator('.drawer-backdrop');
	await expect(overlay).toBeVisible();
	await overlay.click({ position: { x: 370, y: 400 } });
	await expect(drawer).toHaveCount(0);
});

test('selecting a nav link navigates and auto-closes the drawer', async ({ page }) => {
	await page.getByRole('button', { name: 'Open navigation' }).click();
	const drawer = page.getByRole('dialog', { name: 'Main navigation' });
	await drawer.getByRole('link', { name: 'Collections', exact: true }).click();

	await page.waitForURL('**/collections');
	// afterNavigate closes the drawer.
	await expect(page.getByRole('dialog', { name: 'Main navigation' })).toHaveCount(0);
	await expect(page.getByRole('button', { name: 'Open navigation' })).toBeVisible();
});
