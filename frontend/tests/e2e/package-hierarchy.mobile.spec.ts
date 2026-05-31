import { test, expect } from '@playwright/test';
import { seedAdmin, getAuthToken, loginAsAdmin, createSet, createPackage } from './fixtures';

// ADR-229 follow-up: the package page's hierarchy sidebar gets the same mobile
// treatment as the view page — a full-height fixed left overlay drawer (the
// toggle opens it, a backdrop closes it) instead of an inline 280px column.

let packageId = '';

test.beforeAll(async () => {
	await seedAdmin();
	const token = await getAuthToken();
	const set = await createSet(undefined, token, { name: 'Mobile Pkg Hierarchy Set' });
	const pkg = await createPackage(undefined, token, {
		name: 'Mobile Hierarchy Package',
		set_id: set.id as string
	});
	packageId = pkg.id as string;
});

test('package hierarchy toggle opens a full-height overlay drawer on mobile', async ({ page }) => {
	test.slow();
	await loginAsAdmin(page);
	await page.goto(`/packages/${packageId}`);
	await expect(page.getByRole('button', { name: 'Toggle hierarchy sidebar' }).first()).toBeVisible({
		timeout: 15_000
	});

	const aside = page.locator('[data-hierarchy-sidebar]');
	await page.getByRole('button', { name: 'Toggle hierarchy sidebar' }).first().click();
	await expect(aside).toBeVisible();

	// Fixed overlay (not the inline sticky column) and fills the viewport.
	await expect(aside).toHaveCSS('position', 'fixed');
	const vh = await page.evaluate(() => window.innerHeight);
	const box = await aside.boundingBox();
	expect(box!.height).toBeGreaterThan(vh * 0.8);

	// Backdrop closes it (tap the strip right of the ≤320px drawer).
	await page.getByRole('button', { name: 'Close hierarchy' }).click({ position: { x: 370, y: 400 } });
	await expect(aside).toBeHidden();
});
