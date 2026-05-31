import { test, expect } from '@playwright/test';
import { seedAdmin, getAuthToken, loginAsAdmin } from './fixtures';

// Phase 2 of the mobile-responsive rollout (ADR-229 / SPEC-229-A).
// On mobile the two-column `auto 1fr` definition grids on detail pages collapse
// to a single column (.detail-grid + the <768px media query), and the section
// tab bar scrolls horizontally rather than clipping.

const API_BASE = 'http://localhost:8000';

let elementId = '';

test.beforeAll(async () => {
	await seedAdmin();
	const token = await getAuthToken();
	const res = await fetch(`${API_BASE}/api/elements`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
		body: JSON.stringify({ element_type: 'class', name: 'Mobile Detail Stack Element', data: {} })
	});
	if (!res.ok) throw new Error(`create element failed: ${res.status} ${await res.text()}`);
	elementId = (await res.json()).id as string;
});

test('detail definition grid collapses to a single column on mobile', async ({ page }) => {
	test.slow(); // login + page load; absorb rate-limit back-off under full-suite load
	await loginAsAdmin(page);
	await page.goto(`/elements/${elementId}`);
	await page.getByRole('tab', { name: 'Details' }).click();

	const grid = page.locator('.detail-grid').first();
	await expect(grid).toBeVisible();

	// A single grid column resolves to one track (e.g. "393px"); a two-column
	// grid resolves to two space-separated tracks. Assert exactly one track.
	const columns = await grid.evaluate((el) => getComputedStyle(el).gridTemplateColumns);
	expect(columns.trim().split(/\s+/)).toHaveLength(1);
});

test('section tab bar is horizontally scrollable, not clipped', async ({ page }) => {
	test.slow(); // login + page load; absorb rate-limit back-off under full-suite load
	await loginAsAdmin(page);
	await page.goto(`/elements/${elementId}`);

	const tablist = page.getByRole('tablist', { name: 'Element sections' });
	await expect(tablist).toBeVisible();
	// overflow-x-auto keeps every tab reachable even when they exceed the width.
	const overflowX = await tablist.evaluate((el) => getComputedStyle(el).overflowX);
	expect(overflowX).toBe('auto');
});
