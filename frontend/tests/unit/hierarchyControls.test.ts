// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves them at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Issue #27: the hierarchy panel buttons across the Dashboard and the
 * Views index were inconsistent. The user asked for a 2-button
 * standard:
 *   1. + New     → drop-down to create View / Package
 *   2. Show      → drop-down to toggle Diagrams / Text in the tree
 *      (packages are always shown).
 *
 * Both pages now use a shared `HierarchyControls.svelte` component.
 */

const ROOT = resolve(import.meta.dirname, '../..');
const COMPONENT = resolve(ROOT, 'src/lib/components/HierarchyControls.svelte');
const DASHBOARD = resolve(ROOT, 'src/routes/+page.svelte');
const VIEWS_INDEX = resolve(ROOT, 'src/routes/views/+page.svelte');
const TREE_NODE = resolve(ROOT, 'src/lib/components/TreeNode.svelte');

describe('HierarchyControls (issue #27)', () => {
	it('the shared component exists', () => {
		expect(existsSync(COMPONENT)).toBe(true);
	});

	it('exposes the four documented callbacks', () => {
		const src = readFileSync(COMPONENT, 'utf-8');
		expect(src).toMatch(/oncreateview:/);
		expect(src).toMatch(/oncreatepackage:/);
		expect(src).toMatch(/onShowDiagrams:/);
		expect(src).toMatch(/onShowText:/);
	});

	it('renders the two dropdowns ("+ New" and "Show")', () => {
		const src = readFileSync(COMPONENT, 'utf-8');
		expect(src).toMatch(/\+ New/);
		expect(src).toMatch(/Show/);
		// Reassures the user that the missing Packages toggle is intentional.
		expect(src).toMatch(/Packages are always shown/);
	});

	it('Dashboard uses HierarchyControls and removes the old + New inline submenu', () => {
		const src = readFileSync(DASHBOARD, 'utf-8');
		expect(src).toMatch(/import HierarchyControls/);
		expect(src).toMatch(/<HierarchyControls/);
		// The temporary v5.1.0 "View → Diagram | Text" submenu has been removed
		// in favour of the notation pill in the Create dialog.
		expect(src).not.toMatch(/showCreateMenu/);
	});

	it('Views index uses HierarchyControls in place of the standalone New buttons', () => {
		const src = readFileSync(VIEWS_INDEX, 'utf-8');
		expect(src).toMatch(/import HierarchyControls/);
		expect(src).toMatch(/<HierarchyControls/);
	});

	it('TreeNode honours the showDiagrams / showText toggles', () => {
		const src = readFileSync(TREE_NODE, 'utf-8');
		expect(src).toMatch(/showDiagrams\?:\s*boolean/);
		expect(src).toMatch(/showText\?:\s*boolean/);
		expect(src).toMatch(/passesKindFilter/);
		// Packages are always shown.
		expect(src).toMatch(/isPackage \|\| /);
	});
});

describe('HierarchyControls — dropdowns escape overflow containers (issue #169)', () => {
	it('binds the trigger buttons so the dropdown can read their bounding box', () => {
		const src = readFileSync(COMPONENT, 'utf-8');
		// Both trigger buttons get a `bind:this` so we can call
		// getBoundingClientRect() on them before opening the menu.
		expect(src).toMatch(/bind:this=\{newButtonEl\}/);
		expect(src).toMatch(/bind:this=\{showButtonEl\}/);
	});

	it('positions each dropdown with position: fixed so it escapes overflow ancestors', () => {
		const src = readFileSync(COMPONENT, 'utf-8');
		// The Tailwind `absolute` positioning was being clipped by
		// `overflow-y: auto` / `overflow: hidden` on the parent asides
		// (Dashboard, View detail, Packages detail). Switching to
		// `position: fixed` removes that constraint.
		const fixedHits = src.match(/position:\s*fixed/g) ?? [];
		expect(fixedHits.length).toBeGreaterThanOrEqual(2);
		// The old absolute classes should no longer be on the menu containers.
		expect(src).not.toMatch(/<div\s+role="menu"\s+class="absolute/);
	});

	it('computes the menu position from the trigger button rect on open', () => {
		const src = readFileSync(COMPONENT, 'utf-8');
		expect(src).toMatch(/getBoundingClientRect\(\)/);
	});

	it('closes the dropdowns on scroll so they do not detach from the trigger', () => {
		const src = readFileSync(COMPONENT, 'utf-8');
		// Fixed-position menus stay glued to the viewport; close on
		// scroll so the user never sees a floating orphan.
		expect(src).toMatch(/addEventListener\(['"]scroll['"]/);
	});
});

describe('HierarchyControls — compact sizing (issue #162)', () => {
	it('the "+ New" and "Show" trigger buttons use compact px-2 py-1 text-xs', () => {
		const src = readFileSync(COMPONENT, 'utf-8');
		// Both top-level buttons render at the smaller density now.
		const triggers = src.match(/whitespace-nowrap rounded[^"]*px-2 py-1 text-xs/g) ?? [];
		expect(triggers.length).toBeGreaterThanOrEqual(2);
	});

	it('the dropdown menu items use compact px-3 py-1 text-xs', () => {
		const src = readFileSync(COMPONENT, 'utf-8');
		const items = src.match(/block w-full px-3 py-1 text-left text-xs/g) ?? [];
		// Two top-level menus + Diagrams/Text checkboxes use the compact style.
		expect(items.length).toBeGreaterThanOrEqual(2);
	});

	it('does not use the old larger px-3 py-1.5 text-sm sizing anywhere', () => {
		const src = readFileSync(COMPONENT, 'utf-8');
		expect(src).not.toMatch(/px-3 py-1\.5 text-sm/);
		expect(src).not.toMatch(/px-4 py-1\.5 text-sm/);
	});
});
