import { test, expect } from '@playwright/test';
import { seedAdmin, loginAsAdmin } from './fixtures';

// ADR-229 follow-up: the authenticated header's Sign-out button must stay
// inside the header on mobile (the scope breadcrumb is hidden and the action
// group is shrink-0), not spill off the right edge.

test('authenticated Sign out button stays inside the header on mobile', async ({ page }) => {
	test.slow();
	await seedAdmin();
	await loginAsAdmin(page);

	const signOut = page.getByRole('button', { name: /Sign out/ });
	await expect(signOut).toBeVisible();

	const vw = await page.evaluate(() => document.documentElement.clientWidth);
	const box = await signOut.boundingBox();
	expect(box).not.toBeNull();
	// Right edge within the viewport (allow 1px rounding).
	expect(box!.x + box!.width).toBeLessThanOrEqual(vw + 1);

	// And no horizontal overflow on the page overall.
	const overflow = await page.evaluate(
		() => document.documentElement.scrollWidth - document.documentElement.clientWidth
	);
	expect(overflow).toBeLessThanOrEqual(1);
});
