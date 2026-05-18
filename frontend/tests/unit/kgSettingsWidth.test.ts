import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * KG settings dropdown width (v6.11.1).
 *
 * Bug: after v6.9.0 (ADR-199) split the Visibility tab into Nodes,
 * Relationships, and Display, the "Relationships" label didn't fit
 * within the 220px min-width popover — it wrapped or clipped.
 *
 * Fix: bump min-width to 300px and add `whitespace-nowrap` to each
 * tab button so labels stay on one line regardless of container size.
 */

const src = readFileSync(
	resolve(__dirname, '../../src/lib/components/KnowledgeGraphSettings.svelte'),
	'utf-8',
);

describe('KG settings popover width (v6.11.1)', () => {
	it('uses min-width: 300px on the popover container', () => {
		expect(src).toMatch(/min-width:\s*300px/);
	});

	it('no longer uses the old 220px min-width', () => {
		expect(src).not.toMatch(/min-width:\s*220px/);
	});

	it('applies whitespace-nowrap to each tab button', () => {
		// Each of the three tab buttons gets the class so labels never
		// wrap regardless of any future container changes.
		const tabButtonCount = (src.match(/flex-1\s+whitespace-nowrap\s+px-3\s+py-2\s+text-xs\s+font-medium/g) || []).length;
		expect(tabButtonCount).toBe(3);
	});
});
