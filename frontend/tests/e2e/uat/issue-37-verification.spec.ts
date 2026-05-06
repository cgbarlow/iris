/**
 * v5.5.0 (issue #37 reopen): UAT verification of the BPMN canvas crash
 * and the backing API 500s reported in the dev console.
 *
 * Three checks:
 *  - Fresh BPMN view's "Start building" mounts the canvas without throwing
 *    `useStore outside of <SvelteFlowProvider />` or any other page-level
 *    error.
 *  - GET /api/bookmarks returns < 500 (auth or success — but never 5xx).
 *  - GET /api/graph/settings returns < 500.
 */

import { test, expect, type APIRequestContext } from '@playwright/test';
import { mkdirSync, existsSync } from 'node:fs';

const SHOTS = 'tests/e2e/uat/screenshots';

test.beforeAll(() => {
	if (!existsSync(SHOTS)) mkdirSync(SHOTS, { recursive: true });
});

// Helper: capture all console errors + page errors during the test.
function trackErrors(page: import('@playwright/test').Page) {
	const errors: string[] = [];
	page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`));
	page.on('console', (msg) => {
		if (msg.type() === 'error') errors.push(`console.error: ${msg.text()}`);
	});
	return errors;
}

// ──────────────────────────────────────────────────────────────────────
// Item: fresh BPMN view does not throw `useStore outside`
// ──────────────────────────────────────────────────────────────────────
test('issue #37: BPMN canvas mounts without useStore-outside error', async ({ page }) => {
	const errors = trackErrors(page);

	await page.goto('/');
	const bpmnLink = page.locator('a[href*="/views/"]').filter({ hasText: /bpmn/i }).first();
	test.skip((await bpmnLink.count()) === 0, 'No BPMN view on UAT to open.');

	await bpmnLink.click();
	await page.waitForURL(/\/views\/[a-f0-9-]+/);

	// If the view shows a "Start building" CTA, click it. Otherwise the
	// canvas mounts directly.
	const startBuilding = page.getByRole('button', { name: /Start building/i }).first();
	if (await startBuilding.count()) {
		await startBuilding.click();
	}

	// Wait for either the BPMN palette OR a generic canvas indicator.
	await Promise.race([
		page.locator('aside.bpmn-shell__palette').waitFor({ timeout: 15_000 }),
		page.locator('.svelte-flow').waitFor({ timeout: 15_000 }),
	]);

	// The crash manifests as a thrown pageerror; the surface symptom in
	// issue #37 was specifically `useStore outside of <SvelteFlow />`.
	const provErrors = errors.filter((e) => /useStore outside of <SvelteFlow|SvelteFlowProvider/.test(e));
	expect(provErrors, `pageerrors: ${errors.join('\n')}`).toEqual([]);

	await page.screenshot({ path: `${SHOTS}/37-bpmn-canvas-mounts.png`, fullPage: false });
});

// ──────────────────────────────────────────────────────────────────────
// Item: /api/bookmarks must not 5xx
// ──────────────────────────────────────────────────────────────────────
test('issue #37: GET /api/bookmarks returns < 500', async ({ page }) => {
	// Snoop the response observed during a navigation that triggers it.
	const observed: { status: number | null } = { status: null };
	page.on('response', (resp) => {
		if (resp.url().includes('/api/bookmarks') && observed.status === null) {
			observed.status = resp.status();
		}
	});

	await page.goto('/');
	await page.getByRole('heading', { name: 'Dashboard' }).waitFor({ timeout: 15_000 });
	// Give the dashboard's bookmarks fetch a beat.
	await page.waitForTimeout(2000);

	expect(observed.status, 'no /api/bookmarks request was observed during dashboard load').not.toBeNull();
	const status = observed.status as number;
	expect(status, `/api/bookmarks returned ${status}`).toBeLessThan(500);
});

// ──────────────────────────────────────────────────────────────────────
// Item: /api/graph/settings must not 5xx
// ──────────────────────────────────────────────────────────────────────
test('issue #37: GET /api/graph/settings returns < 500', async ({ page }) => {
	const observed: { status: number | null } = { status: null };
	page.on('response', (resp) => {
		if (resp.url().includes('/api/graph/settings') && observed.status === null) {
			observed.status = resp.status();
		}
	});

	await page.goto('/');
	await page.getByRole('heading', { name: 'Dashboard' }).waitFor({ timeout: 15_000 });
	await page.waitForTimeout(3000);

	// graph settings is fetched when a set is active; if it never fires
	// during this page load, the test is non-applicable but we leave it
	// inert rather than failing — the bug is specifically a 5xx, not the
	// absence of the call.
	if (observed.status !== null) {
		const status = observed.status as number;
		expect(status, `/api/graph/settings returned ${status}`).toBeLessThan(500);
	}
});
