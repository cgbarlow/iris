/**
 * Packages-detail hierarchy sidebar uniformity (ADR-194, issue #162).
 *
 * The packages-detail page used to roll its own "+ Child" dropdown +
 * "Diagrams" toggle inside the hierarchy sidebar — different look,
 * different prop shape on TreeNode — while Dashboard and View-detail
 * used the shared HierarchyControls component. Issue #162 closes that
 * DRY gap.
 *
 * Static-parser style for parity with hierarchyControls.test.ts and
 * packageRelationshipsTab.test.ts.
 */
// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const ROOT = resolve(import.meta.dirname, '../..');
const PKG_DETAIL = resolve(ROOT, 'src/routes/packages/[id]/+page.svelte');

describe('Packages detail page hierarchy — uses shared HierarchyControls', () => {
	it('imports HierarchyControls', () => {
		const src = readFileSync(PKG_DETAIL, 'utf-8');
		expect(src).toMatch(/import HierarchyControls from '\$lib\/components\/HierarchyControls\.svelte'/);
	});

	it('mounts HierarchyControls in the hierarchy sidebar', () => {
		const src = readFileSync(PKG_DETAIL, 'utf-8');
		expect(src).toContain('<HierarchyControls');
	});

	it("wires the dropdown's create handlers to the existing child-creation dialogs", () => {
		const src = readFileSync(PKG_DETAIL, 'utf-8');
		// The shared component takes oncreatepackage / oncreateview; the
		// packages page maps them to its child-creation dialog flags.
		expect(src).toMatch(/oncreatepackage=\{[^}]*showCreateChildPackageDialog\s*=\s*true/);
		expect(src).toMatch(/oncreateview=\{[^}]*showCreateChildDiagramDialog\s*=\s*true/);
	});

	it('removes the bespoke "+ Child" dropdown trigger that used to live inline', () => {
		const src = readFileSync(PKG_DETAIL, 'utf-8');
		// The old inline dropdown was driven by a ``showChildMenu`` flag —
		// HierarchyControls owns its own menu state now.
		expect(src).not.toMatch(/showChildMenu\s*=\s*\$state/);
		expect(src).not.toMatch(/\+ Child/);
	});

	it('normalises the TreeNode props to showDiagrams / showText (drops showDiagramsOnly)', () => {
		const src = readFileSync(PKG_DETAIL, 'utf-8');
		// Either the explicit ``showDiagrams={showDiagrams}`` form or
		// the Svelte 5 ``{showDiagrams}`` shorthand is accepted.
		expect(src).toMatch(/<TreeNode[^/>]*(showDiagrams=|\{showDiagrams\})/);
		expect(src).toMatch(/<TreeNode[^/>]*(showText=|\{showText\})/);
		expect(src).not.toMatch(/showDiagramsOnly=\{treeDiagramsOnly\}/);
	});
});
