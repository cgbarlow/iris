/**
 * User-guide screenshot generator (SPEC-122-A).
 *
 * Walks the app as an authenticated admin and writes viewport PNGs to
 * `frontend/static/guide/`. Invoked on demand via `npm run screenshots`
 * — not part of the regular `test:e2e` run because it needs a seeded
 * admin account + live data to produce meaningful images.
 *
 * Re-run whenever the UI changes meaningfully; commit the updated PNGs
 * so the deployed /guide pages serve them without Playwright on Render.
 */

import { test } from '@playwright/test';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loginAsAdmin, seedAdmin } from '../e2e/fixtures';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const STATIC_GUIDE = path.resolve(HERE, '../../static/guide');

// Each screenshot maps to an image referenced from a markdown page in
// src/lib/guide/*.md. Order is guide-reading order so a sequential
// generation produces a coherent set.
const SHOTS = [
	{ name: 'dashboard', url: '/' },
	{ name: 'collections', url: '/collections' },
	{ name: 'sets', url: '/sets' },
	// Packages don't have a list page — show a sample package detail
	// if we can find one; fall back to views.
	{ name: 'packages', url: '/views' },
	{ name: 'diagrams', url: '/views' },
	// Knowledge graph embeds on the dashboard once collection scope is set.
	// Leaving this identical to `dashboard` is fine — the markdown can use
	// the same image for both pages.
	{ name: 'knowledge-graph', url: '/' },
	// Search rendering uses `?q=` on the dashboard so the search results
	// panel is visible when the screenshot fires.
	{ name: 'search', url: '/?q=set' },
	{ name: 'ask-ai', url: '/ask' },
	{ name: 'bookmarks', url: '/bookmarks' },
	{ name: 'admin', url: '/admin/users' },
	// Added v4.2.0 for the expanded guide (SPEC-122-A amendment).
	{ name: 'imports', url: '/import' },
	{ name: 'recycle-bin', url: '/recycle-bin' },
	{ name: 'admin-banner', url: '/admin/settings' },
	{ name: 'admin-users', url: '/admin/users' },
	{ name: 'admin-audit', url: '/admin/audit' },
	{ name: 'admin-locks', url: '/admin/locks' },
];

test.describe.configure({ mode: 'serial', timeout: 60_000 });

test('generate user-guide screenshots', async ({ page, baseURL }) => {
	await seedAdmin(baseURL);
	await loginAsAdmin(page);

	for (const shot of SHOTS) {
		await page.goto(shot.url);
		// Wait for any network settle; use networkidle for pages that
		// eagerly load lists, and a brief delay for the force-graph to
		// paint when the dashboard is in view.
		await page.waitForLoadState('networkidle').catch(() => undefined);
		await page.waitForTimeout(shot.name === 'knowledge-graph' ? 3000 : 500);
		await page.screenshot({
			path: path.join(STATIC_GUIDE, `${shot.name}.png`),
			fullPage: false,
		});
	}
});
