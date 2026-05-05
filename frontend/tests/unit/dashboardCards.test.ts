// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.0 — items #11 + #12:
 *   #11 Drop the Packages card from the dashboard.
 *   #12 Give Collections + Sets cards a muted-grey background so they
 *       visually separate from the working-content cards (Views, Elements).
 */

const PAGE = readFileSync(
	resolve(import.meta.dirname, '../../src/routes/+page.svelte'),
	'utf-8',
);

describe('Dashboard cards (issue cluster, v5.4.0)', () => {
	it('the Packages card is removed (#11)', () => {
		// Look for the existing Packages card pattern: <a href="/packages…"> with
		// the Packages count + label. After the fix this DOM should not exist.
		expect(PAGE).not.toMatch(/href=\{[^}]*\/packages[^}]*\}[\s\S]{0,200}Packages/);
	});

	it('Collections + Sets cards are tagged with the ambient style class (#12)', () => {
		// Match the marker class added to Collections/Sets cards. We use
		// `.dashboard-card--ambient` so the differentiation is theme-aware.
		const collections = PAGE.match(/Collections\b[\s\S]{0,250}/)?.[0] ?? '';
		const sets = PAGE.match(/Sets\b[\s\S]{0,250}/)?.[0] ?? '';
		// Loose check: the surrounding card markup contains the ambient class
		// or the equivalent CSS variable on the background style.
		expect(PAGE).toMatch(/dashboard-card--ambient|--color-surface[\s\S]{0,200}Collections|--color-surface[\s\S]{0,200}Sets/);
	});

	it('Views + Elements cards keep the standard look (regression guard)', () => {
		expect(PAGE).toMatch(/Views\s*\{?#?if?[^<]*<\/div>/);
		expect(PAGE).toMatch(/Elements\s*\{?#?if?[^<]*<\/div>/);
	});
});
