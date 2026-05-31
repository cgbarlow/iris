import { test, expect, type Page } from '@playwright/test';
import { seedAdmin, getAuthToken, loginAsAdmin } from './fixtures';

// Phase 2 of the mobile-responsive rollout (ADR-229 / SPEC-229-A).
// No page should scroll horizontally at the Pixel 5 viewport (393px). A
// horizontal overflow on mobile is the classic symptom of a fixed-width or
// non-wrapping desktop layout leaking through.

const API_BASE = 'http://localhost:8000';

async function expectNoHorizontalOverflow(page: Page) {
	const overflow = await page.evaluate(
		() => document.documentElement.scrollWidth - document.documentElement.clientWidth
	);
	// Allow 1px for sub-pixel rounding.
	expect(overflow, 'horizontal overflow (scrollWidth − clientWidth)').toBeLessThanOrEqual(1);
}

test.describe('no horizontal overflow on mobile', () => {
	// Anonymous-reachable browse surfaces (ADR-123) — no seeding needed.
	for (const path of ['/', '/collections', '/sets', '/elements', '/ask']) {
		test(`browse page ${path} does not overflow`, async ({ page }) => {
			await page.goto(path);
			await expect(page.getByRole('button', { name: 'Open navigation' })).toBeVisible();
			await expectNoHorizontalOverflow(page);
		});
	}

	// A populated element-detail page exercises the detail grids and the wide
	// metadata/relationship tables, which are the real overflow risks.
	test('populated element-detail page does not overflow', async ({ page }) => {
		test.slow(); // seeds + logs in; absorb API rate-limit back-off under full-suite load
		await seedAdmin();
		const token = await getAuthToken();
		const res = await fetch(`${API_BASE}/api/elements`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
			body: JSON.stringify({
				element_type: 'class',
				name: 'Mobile Overflow Probe Element',
				data: {
					attributes: [
						{ name: 'identifier', type: 'string', scope: 'Public', notes: 'primary key for the record' },
						{ name: 'createdAtTimestamp', type: 'datetime', scope: 'Private', notes: 'set on insert' },
						{ name: 'longDescriptiveFieldName', type: 'text', scope: 'Protected', notes: 'free text notes column' }
					]
				}
			})
		});
		if (!res.ok) throw new Error(`create element failed: ${res.status} ${await res.text()}`);
		const elementId = (await res.json()).id as string;

		await loginAsAdmin(page);
		await page.goto(`/elements/${elementId}`);
		await page.getByRole('tab', { name: 'Details' }).click();
		await expect(page.locator('.detail-grid').first()).toBeVisible();
		await expectNoHorizontalOverflow(page);
	});
});
