// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves them at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Issue #30: dropdowns previously used `absolute right-0`, which on the
 * Dashboard's left-aligned hierarchy panel pushed the menu under the
 * AppShell nav. They now use `left-0` so the menu extends rightwards
 * from the button — visible in both the Dashboard panel (panel sits on
 * the page-content left edge) and the Views toolbar (button sits among
 * other toolbar items with room to the right).
 */
const SRC = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/components/HierarchyControls.svelte'),
	'utf-8',
);

describe('HierarchyControls dropdown alignment (issue #30)', () => {
	it('the + New menu opens to the right (left-anchored)', () => {
		expect(SRC).toMatch(/min-w-\[160px\]/);
		const newMenu = SRC.match(/class="([^"]*min-w-\[160px\][^"]*)"/)?.[1] ?? '';
		expect(newMenu).toContain('left-0');
		expect(newMenu).not.toContain('right-0');
	});

	it('the Show menu opens to the right (left-anchored)', () => {
		expect(SRC).toMatch(/min-w-\[180px\]/);
		const showMenu = SRC.match(/class="([^"]*min-w-\[180px\][^"]*)"/)?.[1] ?? '';
		expect(showMenu).toContain('left-0');
		expect(showMenu).not.toContain('right-0');
	});

	it('regression guard — neither menu uses right-0', () => {
		const occurrences = SRC.match(/absolute right-0/g) ?? [];
		expect(occurrences).toHaveLength(0);
	});
});
