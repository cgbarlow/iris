/**
 * v5.6.0 (issue #52): Playwright UAT spec for ArchiMate Open Exchange XML
 * import. Drives the live UAT site:
 *  1. Uploads the real-world MSD fixture via /import — asserts the summary
 *     reports ~127 elements / ~977 relationships / 1 auto-generated diagram.
 *  2. Opens the auto-generated Overview diagram and confirms the canvas
 *     renders ≥100 nodes without throwing.
 *  3. Opens /elements filtered to the test set and confirms a known
 *     imported element ("Reciprocal Australia") is listed.
 *
 * Pre-req: feature is deployed to UAT (run after promotion). Until then
 * the suite will fail with a 404 on /api/import/archimate, which is the
 * expected red state.
 */

import { test, expect } from '@playwright/test';
import { existsSync, mkdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const SHOTS = 'tests/e2e/uat/screenshots';
const FIXTURE = resolve(__dirname, '../../../../docs/reference/ArchiMate/msd-map.xml');
const SIDECAR = resolve(__dirname, '.auth/archimate-set.json');

test.beforeAll(() => {
	if (!existsSync(SHOTS)) mkdirSync(SHOTS, { recursive: true });
});

function trackErrors(page: import('@playwright/test').Page): string[] {
	const errors: string[] = [];
	page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`));
	page.on('console', (msg) => {
		if (msg.type() === 'error') errors.push(`console.error: ${msg.text()}`);
	});
	return errors;
}

function readSidecar(): { set_id: string; set_name: string } {
	const raw = readFileSync(SIDECAR, 'utf-8');
	return JSON.parse(raw);
}

test('issue #52: imports MSD ArchiMate OEX file and reports summary', async ({ page }) => {
	const errors = trackErrors(page);
	const { set_id, set_name } = readSidecar();

	await page.goto('/import');
	await expect(page.getByRole('heading', { name: 'Import' })).toBeVisible();

	// Pick the fixture via the hidden file input.
	const input = page.locator('input[type="file"]');
	await input.setInputFiles(FIXTURE);

	// SetSelector should be visible now; choose the ArchiMate Test set by
	// matching its name in the visible options.
	const setSelector = page.locator('select, [role="combobox"]').first();
	if (await setSelector.count()) {
		// Best-effort: try a select first, fall back to typing in a combobox.
		try {
			await setSelector.selectOption({ label: set_name });
		} catch {
			await setSelector.fill(set_name);
		}
	}

	await page.screenshot({ path: `${SHOTS}/52-01-pre-import.png`, fullPage: true });

	// Confirm dialog ("Are you sure you want to import to existing set ...")
	page.once('dialog', (d) => d.accept());

	// Hit Import — wait for either the summary panel or an error banner.
	await page.getByRole('button', { name: /^Import(?:\s|$)/i }).click();

	// The import has to ingest 977 relationships → comfortably under 90s on Render.
	await expect(page.getByRole('heading', { name: 'Import Complete' })).toBeVisible({
		timeout: 90_000,
	});

	const summaryText = await page
		.locator('div:has(> h2:has-text("Import Complete"))')
		.first()
		.textContent();
	expect(summaryText).toBeTruthy();
	const elementsCreated = Number(summaryText!.match(/(\d+)\s*Elements/)?.[1] ?? '0');
	const relsCreated = Number(summaryText!.match(/(\d+)\s*Relationships/)?.[1] ?? '0');
	const diagramsCreated = Number(summaryText!.match(/(\d+)\s*Diagrams/)?.[1] ?? '0');
	expect(elementsCreated).toBeGreaterThanOrEqual(120);
	expect(relsCreated).toBeGreaterThanOrEqual(900);
	expect(diagramsCreated).toBe(1);

	await page.screenshot({ path: `${SHOTS}/52-02-import-summary.png`, fullPage: true });

	// No page-level errors during the import.
	const fatal = errors.filter((e) => !/keep-alive|favicon|404 .* image/i.test(e));
	expect(fatal, `pageerrors: ${fatal.join('\n')}`).toHaveLength(0);

	// Stash the set id for follow-on tests.
	expect(set_id).toBeTruthy();
});

test('issue #52: opens the auto-generated Overview diagram', async ({ page }) => {
	const errors = trackErrors(page);
	const { set_id } = readSidecar();

	await page.goto(`/views?set_id=${set_id}`);

	// Find a diagram whose title contains "Overview" — the auto-generated one.
	const overviewLink = page
		.locator('a[href*="/views/"]')
		.filter({ hasText: /Overview/i })
		.first();
	await expect(overviewLink).toBeVisible({ timeout: 15_000 });
	await overviewLink.click();
	await page.waitForURL(/\/views\/[a-f0-9-]+/);

	// Wait for the canvas to mount with a population of nodes.
	await page.locator('.svelte-flow__node').first().waitFor({ timeout: 30_000 });
	const count = await page.locator('.svelte-flow__node').count();
	expect(count).toBeGreaterThanOrEqual(100);

	await page.screenshot({ path: `${SHOTS}/52-03-overview-canvas.png`, fullPage: true });

	const fatal = errors.filter((e) => !/keep-alive|favicon|404 .* image/i.test(e));
	expect(fatal, `pageerrors: ${fatal.join('\n')}`).toHaveLength(0);
});

test('issue #52: imported elements appear in /elements list', async ({ page }) => {
	const { set_id } = readSidecar();
	await page.goto(`/elements?set_id=${set_id}`);
	// Look for a known constraint from the MSD fixture.
	await expect(page.getByText(/Reciprocal Australia/i).first()).toBeVisible({
		timeout: 15_000,
	});
	await page.screenshot({ path: `${SHOTS}/52-04-elements-list.png`, fullPage: true });
});
