// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Issue #69 / BPMN-03 wiring guard.
 *
 * `<SvelteFlow>` in UnifiedCanvas.svelte must wire BOTH:
 *   - `isValidConnection={onbeforeconnect}` (already in place via #46/9)
 *   - `onconnect={...}` invoking `handleConnect(c.source, c.target)` so
 *     drag-handle connections route through the same path keyboard / connect-
 *     mode connections take. Without `onconnect`, xyflow auto-adds a typeless
 *     edge (Handle.svelte:108 → addEdge util appends `{...connection, id}`),
 *     `onconnectnodes` never fires, and the BPMN shell's `/api/relationships`
 *     POST is never made.
 *
 * Static-parser test: catches any future refactor that drops the wiring.
 */

const SRC = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/UnifiedCanvas.svelte'),
	'utf-8',
);

describe('UnifiedCanvas <SvelteFlow> drag-connect wiring (issue #69)', () => {
	// Extract the editing <SvelteFlow …> opening tag (the one with bind:edges,
	// not the browse-mode read-only one). Arrow-function props like
	// `() => onnodedragstart?.()` contain `>` inside the value, so a lazy
	// `[^>]*?` won't reach the real closing tag — instead, find the start
	// position then scan forward to the first `>` whose preceding non-space
	// character is NOT `=` (i.e., not an `=>` arrow).
	function extractEditingFlowOpenTag(src: string): string {
		const startIdx = src.search(/<SvelteFlow\b[^>]*bind:edges/);
		expect(startIdx, 'editing <SvelteFlow> with bind:edges').toBeGreaterThanOrEqual(0);
		for (let i = startIdx; i < src.length; i++) {
			if (src[i] !== '>') continue;
			// Walk back over whitespace and find the previous non-ws char.
			let j = i - 1;
			while (j >= 0 && /\s/.test(src[j])) j--;
			if (src[j] === '=') continue; // it's `=>`, keep scanning
			return src.slice(startIdx, i + 1);
		}
		throw new Error('no closing > for editing <SvelteFlow>');
	}
	const block = extractEditingFlowOpenTag(SRC);

	it('wires onconnect on the editing SvelteFlow', () => {
		expect(block, 'onconnect={…} present').toMatch(/\bonconnect\s*=\s*\{/);
	});

	it('wires isValidConnection (preserved from #46/9 — does not regress)', () => {
		expect(block).toMatch(/\bisValidConnection\s*=\s*\{/);
	});

	it('the onconnect handler patches edge type and notifies the consumer', () => {
		// The handler may be inline or a named function. Either way, the file
		// as a whole must reference both patchConnectedEdgeType (the type-fix
		// helper for issue #69) and onconnectnodes (the consumer-notify path).
		expect(SRC, 'patches edge type via patchConnectedEdgeType')
			.toMatch(/patchConnectedEdgeType\s*\(/);
		expect(SRC, 'invokes onconnectnodes consumer if set')
			.toMatch(/onconnectnodes\??\s*\(/);
	});

	it('imports patchConnectedEdgeType from $lib/canvas/edgeOnConnect', () => {
		expect(SRC).toMatch(/import\s+\{[^}]*patchConnectedEdgeType[^}]*\}\s+from\s+['"]\$lib\/canvas\/edgeOnConnect['"]/);
	});
});
