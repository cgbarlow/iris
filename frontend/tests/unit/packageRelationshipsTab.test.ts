import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Package detail Relationships tab tests (v6.7.4, ADR-188, issue #157).
 *
 * The package detail page was missing the relationships tab that
 * lists elements attached to the package — the views/diagrams pages
 * had a comparable affordance after the v6.7.0 element→package
 * membership work (ADR-184) but the package side had been overlooked.
 *
 * These tests are static-parser style (same pattern as
 * dashboardHierarchy.test.ts) to keep the package page route
 * lightweight to verify.
 */

const pkgPageSrc = readFileSync(
	resolve(__dirname, '../../src/routes/packages/[id]/+page.svelte'),
	'utf-8',
);

describe('Package detail relationships tab — state', () => {
	it("adds 'relationships' to the activeTab union", () => {
		expect(pkgPageSrc).toContain(
			"$state<'details' | 'versions' | 'relationships'>",
		);
	});

	it('declares packageElements state and loaded flags', () => {
		expect(pkgPageSrc).toContain('packageElements');
		expect(pkgPageSrc).toContain('packageElementsLoading');
		expect(pkgPageSrc).toContain('packageElementsLoaded');
		expect(pkgPageSrc).toContain('packageElementsTotal');
	});
});

describe('Package detail relationships tab — API call', () => {
	it('calls GET /api/packages/{id}/elements via apiFetch', () => {
		expect(pkgPageSrc).toMatch(/\/api\/packages\/\$\{[^}]+\}\/elements/);
	});

	it('uses a paginated fetch with page_size query param', () => {
		expect(pkgPageSrc).toContain('page_size=');
	});
});

describe('Package detail relationships tab — UI affordance', () => {
	it('renders a Relationships tab button alongside Details and Version History', () => {
		expect(pkgPageSrc).toContain('Relationships');
		expect(pkgPageSrc).toContain('Details');
		expect(pkgPageSrc).toContain('Version History');
	});

	it('Relationships tab is keyboard/screen-reader accessible via aria-selected', () => {
		expect(pkgPageSrc).toContain("aria-selected={activeTab === 'relationships'}");
	});

	it('renders an Elements table with links to /elements/{id}', () => {
		expect(pkgPageSrc).toContain('href="/elements/{el.id}"');
	});

	it('shows an empty-state message when the package has no elements', () => {
		expect(pkgPageSrc).toContain('No elements in this package');
	});

	it('lazy-loads elements only when the tab is first activated', () => {
		expect(pkgPageSrc).toContain('activateRelationshipsTab');
		// The activation handler should guard against re-loading.
		expect(pkgPageSrc).toContain('!packageElementsLoaded');
	});
});
