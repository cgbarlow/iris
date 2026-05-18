import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Packages detail — Relationships auto-reload on navigation
 * (v6.10.1, ADR-201, follows ADR-195).
 *
 * ADR-195 fixed the stale-data bug by resetting the relationships
 * state at the top of `loadPackage`. That removed the wrong-package's
 * elements from view, but left a follow-up bug: if the user was
 * already on the Relationships tab and navigated to a different
 * package from the hierarchy sidebar, the elements list went empty
 * and stayed empty until the user clicked the Relationships tab
 * heading (which calls `activateRelationshipsTab` → loadPackageElements).
 *
 * Fix: at the end of `loadPackage`, if `activeTab === 'relationships'`
 * and we have a `pkg`, kick off `loadPackageElements(pkg.id)` so the
 * tab content rehydrates without requiring a tab-click.
 *
 * Static-parser style.
 */

const pkgPageSrc = readFileSync(
	resolve(__dirname, '../../src/routes/packages/[id]/+page.svelte'),
	'utf-8',
);

function loadPackageBody(): string {
	const start = pkgPageSrc.indexOf('async function loadPackage(');
	expect(start, 'loadPackage function not found').toBeGreaterThan(-1);
	const braceStart = pkgPageSrc.indexOf('{', start);
	let depth = 0;
	let i = braceStart;
	for (; i < pkgPageSrc.length; i++) {
		const ch = pkgPageSrc[i];
		if (ch === '{') depth++;
		else if (ch === '}') {
			depth--;
			if (depth === 0) break;
		}
	}
	return pkgPageSrc.slice(braceStart, i + 1);
}

describe('Package detail — loadPackage auto-reloads relationships on navigation (#173-followup)', () => {
	const body = loadPackageBody();

	it('still resets relationships state at the top (ADR-195 behaviour preserved)', () => {
		expect(body).toMatch(/packageElementsLoaded\s*=\s*false/);
	});

	it("kicks off loadPackageElements when navigating into the Relationships tab", () => {
		// The re-hydration check looks for activeTab === 'relationships'
		// and an existing pkg, then calls loadPackageElements with
		// pkg.id (not the function's `id` argument, since the try/catch
		// may have set pkg to something different if a redirect path
		// existed — keep symmetric with the activate handler).
		expect(body).toMatch(/activeTab\s*===\s*'relationships'/);
		expect(body).toMatch(/loadPackageElements\(pkg\.id\)/);
	});

	it("does not call loadPackageElements if a load is already in flight", () => {
		// Guard prevents stomping a concurrent fetch.
		expect(body).toMatch(/!packageElementsLoading/);
	});
});
