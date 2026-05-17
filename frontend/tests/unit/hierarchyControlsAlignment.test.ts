// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves them at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Issue #30 (original): dropdowns previously used `absolute right-0`,
 * which on the Dashboard's left-aligned hierarchy panel pushed the
 * menu under the AppShell nav. They were switched to `left-0` so the
 * menu extends rightwards from the button.
 *
 * Issue #169 (this rev): the menus are now `position: fixed` with
 * coordinates computed from `getBoundingClientRect()` of the trigger.
 * Same visual outcome (menu opens *right and down* from the trigger,
 * never to the left) but escapes any overflow ancestor.
 */
const SRC = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/components/HierarchyControls.svelte'),
	'utf-8',
);

describe('HierarchyControls dropdown alignment (issues #30, #169)', () => {
	it('the + New menu is positioned from the trigger button rect', () => {
		expect(SRC).toMatch(/min-w-\[160px\]/);
		// New shape: inline style sets `left: {newMenuPos.left}px`, anchored
		// to the trigger's bounding rect left edge (matches the prior left-0
		// intent, but works across overflow contexts).
		expect(SRC).toMatch(/left: \{newMenuPos\.left\}px/);
	});

	it('the Show menu is positioned from the trigger button rect', () => {
		expect(SRC).toMatch(/min-w-\[180px\]/);
		expect(SRC).toMatch(/left: \{showMenuPos\.left\}px/);
	});

	it('regression guard — neither menu opens to the LEFT of the trigger', () => {
		// The original #30 guard: never `right-0` (which would left-align
		// the menu and clip under the AppShell nav). The new positioning
		// uses `r.left` (button's left edge), so a right-aligned variant
		// would manifest as `r.right - menuWidth`. Neither pattern should
		// appear.
		expect(SRC).not.toMatch(/right-0/);
		expect(SRC).not.toMatch(/right:\s*\{[^}]*\}px/);
	});
});
