// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.1 — issue #46 items #2 + #3:
 *  - Show dropdown shows a greyed "Views" section label above the
 *    "Diagrams" checkbox.
 *  - +New dropdown lists Package above View, View visually indented
 *    to read as a child of Package.
 */

const SRC = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/components/HierarchyControls.svelte'),
	'utf-8',
);

describe('HierarchyControls (v5.4.1, issue #46 items #2 + #3)', () => {
	it('Show dropdown contains a greyed "Views" section header above the Diagrams checkbox', () => {
		// Locate the Show menu block (between "Show ▾" and the closing
		// Packages-always-shown footer).
		const showMenuMatch = SRC.match(/Show\s*▾[\s\S]*?Packages are always shown/);
		expect(showMenuMatch, 'Show menu block found').not.toBeNull();
		const showBlock = showMenuMatch![0];

		// "Views" appears, marked up as non-interactive with muted colour.
		expect(showBlock).toMatch(/>\s*Views\s*</);
		// The Views label uses the muted colour token (greyed-out look).
		expect(showBlock).toMatch(/Views[\s\S]{0,400}?var\(--color-muted\)/);
		// "Views" label appears BEFORE the Diagrams checkbox text. Match
		// the label text content (not arbitrary mentions in comments).
		const viewsIdx = showBlock.search(/>\s*Views\s*</);
		const diagramsIdx = showBlock.search(/>\s*Diagrams\s*</);
		expect(viewsIdx).toBeGreaterThan(-1);
		expect(diagramsIdx).toBeGreaterThan(-1);
		expect(viewsIdx).toBeLessThan(diagramsIdx);
	});

	it('+New dropdown lists Package above View, with View indented', () => {
		// Locate the +New menu block (between "+ New ▾" and the closing
		// Show ▾ trigger).
		const newMenuMatch = SRC.match(/\+\s*New\s*▾[\s\S]*?Show\s*▾/);
		expect(newMenuMatch, '+New menu block found').not.toBeNull();
		const newBlock = newMenuMatch![0];

		const packageIdx = newBlock.indexOf('Package');
		const viewIdx = newBlock.indexOf('>View<') >= 0
			? newBlock.indexOf('>View<')
			: newBlock.search(/>\s*View\s*</);
		expect(packageIdx).toBeGreaterThan(-1);
		expect(viewIdx).toBeGreaterThan(-1);
		// Package button should appear BEFORE View.
		expect(packageIdx).toBeLessThan(viewIdx);

		// View button has an indent class (pl-7, pl-8, ml-4, etc) — accept any
		// of the conventional Tailwind left-padding/margin tokens.
		const viewBtnSnippet = newBlock.slice(viewIdx - 400, viewIdx + 50);
		expect(viewBtnSnippet).toMatch(/(pl-[5-9]|pl-1[0-2]|pl-\[[0-9]+px\]|padding-left)/);
	});
});
