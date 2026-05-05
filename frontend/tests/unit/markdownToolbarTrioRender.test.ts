// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.0 (#8): Add Element / Link Element / Add Diagram should be
 * visible in BPMN + Text + canvas edit modes. Pre-v5.4 they only
 * rendered for the non-sequence, non-text, non-bpmn canvas branch.
 *
 * The handlers themselves already branch on canvasType === 'text'
 * (v5.1.1) — Phase 4 adds the BPMN branch and renders the toolbar
 * for Text + BPMN modes too.
 */

const PAGE = readFileSync(
	resolve(import.meta.dirname, '../../src/routes/views/[id]/+page.svelte'),
	'utf-8',
);

describe('Trio toolbar render in BPMN + Text + canvas edit modes (#8, v5.4.0)', () => {
	it('the trio toolbar mounts on Text views in edit mode', () => {
		// The Text branch renders <TextCanvas …editing /> when editing.
		// Above it (or alongside) there must be Add Element / Link Element /
		// Add Diagram buttons. Expressed as a substring search on the page.
		// Simple form: count all three buttons on the page (≥ 2 occurrences
		// of each — one in the canvas branch, one in BPMN/Text branch).
		const addElement = PAGE.match(/Add Element\b/g) ?? [];
		const linkElement = PAGE.match(/Link Element\b/g) ?? [];
		const addDiagram = PAGE.match(/Add Diagram\b/g) ?? [];
		// Pre-v5.4 each appeared 2× (one in canvas toolbar, one in focus-mode
		// canvas toolbar). After Phase 4 the trio also lands in the Text +
		// BPMN branches, so ≥ 3 each.
		expect(addElement.length).toBeGreaterThanOrEqual(3);
		expect(linkElement.length).toBeGreaterThanOrEqual(3);
		expect(addDiagram.length).toBeGreaterThanOrEqual(3);
	});

	it('handleAddElement has a BPMN branch that creates a node + Element', () => {
		// Mirroring the Text branch in the existing handler — BPMN gets its
		// own branch that POSTs /api/elements and adds a canvas node.
		const fn = PAGE.match(/async function handleAddElement[\s\S]*?\n\t\}/)?.[0] ?? '';
		expect(fn).toMatch(/canvasType\s*===\s*['"]bpmn['"]/);
	});

	it('handleLinkElement has a BPMN branch that binds the picked Element to the selected node', () => {
		const fn = PAGE.match(/function handleLinkElement[\s\S]*?\n\t\}/)?.[0] ?? '';
		expect(fn).toMatch(/canvasType\s*===\s*['"]bpmn['"]/);
		expect(fn).toMatch(/entityId/);
	});

	it('handleInsertDiagram has a BPMN branch that creates a call_activity sub-process', () => {
		const fn = PAGE.match(/function handleInsertDiagram[\s\S]*?\n\t\}/)?.[0] ?? '';
		expect(fn).toMatch(/canvasType\s*===\s*['"]bpmn['"]/);
		expect(fn).toMatch(/call_activity/);
	});
});
