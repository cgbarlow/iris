// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.1 — issue #46 item #1: The /views page toolbar should match the
 * dashboard's ordering — the create control leftmost, auxiliary buttons
 * (Select) to its right. v6.17.0 (#194) replaced HierarchyControls here
 * with a single "New View" button; the ordering rule still holds.
 */

const PAGE = readFileSync(
	resolve(import.meta.dirname, '../../src/routes/views/+page.svelte'),
	'utf-8',
);

describe('Views toolbar ordering (v5.4.1, issue #46 item #1)', () => {
	it('the New View button renders BEFORE the Select button in the views toolbar', () => {
		const createIdx = PAGE.search(/onclick=\{\(\) => \(showCreateDialog = true\)\}/);
		const selectIdx = PAGE.search(/onclick=\{[^}]*selectMode\s*=\s*!selectMode/);
		expect(createIdx).toBeGreaterThan(-1);
		expect(selectIdx).toBeGreaterThan(-1);
		expect(createIdx).toBeLessThan(selectIdx);
	});
});
