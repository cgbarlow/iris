// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.1 — issue #46 item #1: The /views page toolbar should match the
 * dashboard's ordering — HierarchyControls leftmost, auxiliary buttons
 * (Select) to its right.
 */

const PAGE = readFileSync(
	resolve(import.meta.dirname, '../../src/routes/views/+page.svelte'),
	'utf-8',
);

describe('Views toolbar ordering (v5.4.1, issue #46 item #1)', () => {
	it('HierarchyControls renders BEFORE the Select button in the views toolbar', () => {
		// Find the toolbar wrapper — the flex container that holds the page
		// title row's right-side action buttons.
		const hierarchyIdx = PAGE.indexOf('<HierarchyControls');
		const selectIdx = PAGE.search(/onclick=\{[^}]*selectMode\s*=\s*!selectMode/);
		expect(hierarchyIdx).toBeGreaterThan(-1);
		expect(selectIdx).toBeGreaterThan(-1);
		expect(hierarchyIdx).toBeLessThan(selectIdx);
	});
});
