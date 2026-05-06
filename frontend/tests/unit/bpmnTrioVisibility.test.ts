// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.1 — issue #46 items #5 + #12:
 *  - Trio (Add Element / Link Element / Add Diagram) appears EXACTLY
 *    once in the page (the canvas {:else} toolbar, which already covers
 *    Text + BPMN since canvasType !== 'sequence').
 *  - Add Element button is hidden on BPMN (palette already covers that).
 */

const PAGE = readFileSync(
	resolve(import.meta.dirname, '../../src/routes/views/[id]/+page.svelte'),
	'utf-8',
);

describe('Trio toolbar (v5.4.1, issue #46 items #5 + #12)', () => {
	it('removes the duplicate trio from the Text branch and the BPMN branch', () => {
		// The parent canvas toolbar trio (lines ~2687-2716) covers all
		// non-sequence canvases. The FocusView toolbar (lines ~2877-2895)
		// intentionally re-renders the trio because the focus overlay
		// hides the parent toolbar. v5.4.0 incorrectly added third + fourth
		// trios in the Text and BPMN inner branches — those duplicates are
		// what the user reported in #46 item #5.
		//
		// Test: locate the {:else if canvasType === 'text'} branch and the
		// {:else if notation === 'bpmn'} branch (canvas-area side, after the
		// FocusView block) and assert NEITHER branch contains a Link Element
		// or Add Diagram button text.
		const textBranchMatch = PAGE.match(/\{:else if canvasType === 'text'\}[\s\S]*?\{:else if notation === 'bpmn'\}/);
		expect(textBranchMatch, 'text branch found').not.toBeNull();
		const textBranch = textBranchMatch![0];
		expect(textBranch).not.toMatch(/>\s*Link Element\s*</);
		expect(textBranch).not.toMatch(/>\s*Add Diagram\s*</);

		const bpmnBranchMatch = PAGE.match(/\{:else if notation === 'bpmn'\}[\s\S]*?<BpmnAuthoringShell/);
		expect(bpmnBranchMatch, 'bpmn branch found').not.toBeNull();
		const bpmnBranch = bpmnBranchMatch![0];
		expect(bpmnBranch).not.toMatch(/>\s*Link Element\s*</);
		expect(bpmnBranch).not.toMatch(/>\s*Add Diagram\s*</);
	});

	it('Add Element button is gated on notation !== "bpmn" in the parent canvas toolbar', () => {
		// Locate the parent canvas toolbar's Create group (the {#if editing}
		// block right after the canvas {:else}). Within that block, the
		// Add Element button must sit inside a {#if notation !== 'bpmn'}
		// guard.
		const toolbarMatch = PAGE.match(/<!-- Canvas toolbar -->[\s\S]*?<!-- Edit group -->/);
		expect(toolbarMatch, 'canvas toolbar Create group').not.toBeNull();
		const toolbar = toolbarMatch![0];
		const addElementIdx = toolbar.search(/>\s*Add Element\s*</);
		expect(addElementIdx).toBeGreaterThan(-1);
		// Within 400 chars upstream, find the gating {#if}.
		const upstream = toolbar.slice(Math.max(0, addElementIdx - 400), addElementIdx);
		expect(upstream).toMatch(/notation\s*(?:as\s+\w+\s*)?\)?\s*!==?\s*['"]bpmn['"]/);
	});
});
