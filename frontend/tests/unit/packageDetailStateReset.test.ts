import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Package detail per-package state reset (v6.8.4, ADR-195, issue #173 item 3).
 *
 * Bug: the relationships tab cached its elements in `packageElements*`
 * state with `packageElementsLoaded` latched to `true` after first
 * hydration. Navigating to a different package re-ran `loadPackage`
 * but did not reset those flags, so the previous package's elements
 * stayed rendered until a hard browser refresh.
 *
 * Reproduction: visit /packages/A → Relationships tab (hydrates A's
 * elements) → navigate to /packages/B → Relationships tab. B's tab
 * shows A's elements.
 *
 * Fix: reset per-package derived state at the top of `loadPackage`
 * so each navigation starts from a clean slate. Static-parser style
 * to match the rest of this suite.
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

describe('Package detail — loadPackage resets per-package state (issue #173 item 3)', () => {
	const body = loadPackageBody();

	it('resets packageElementsLoaded', () => {
		expect(body).toMatch(/packageElementsLoaded\s*=\s*false/);
	});

	it('resets packageElementsLoading', () => {
		expect(body).toMatch(/packageElementsLoading\s*=\s*false/);
	});

	it('clears packageElements array', () => {
		expect(body).toMatch(/packageElements\s*=\s*\[\]/);
	});

	it('resets packageElementsTotal to 0', () => {
		expect(body).toMatch(/packageElementsTotal\s*=\s*0/);
	});

	it('clears packageElementsError', () => {
		expect(body).toMatch(/packageElementsError\s*=\s*null/);
	});

	it('exits any in-progress inline edit (editingDetails)', () => {
		// If the user was editing Frozen's details and navigated to
		// Pantry, edit-mode would persist with stale field values.
		expect(body).toMatch(/editingDetails\s*=\s*false/);
	});

	it('resets detailsDirty flag', () => {
		expect(body).toMatch(/detailsDirty\s*=\s*false/);
	});
});

describe('Package detail — activateRelationshipsTab guard still in place', () => {
	it('continues to short-circuit when state is hydrated for current package', () => {
		// Behaviour unchanged on the activation side — the reset is in
		// loadPackage, so a tab re-open without navigation still skips
		// the redundant fetch.
		expect(pkgPageSrc).toContain('!packageElementsLoaded && !packageElementsLoading');
	});
});
