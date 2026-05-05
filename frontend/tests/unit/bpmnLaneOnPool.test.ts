// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.0 (#5): xyflow doesn't auto-set `parentId` on visual overlap.
 * The validateBpmn `lane_outside_pool` rule walks parentId correctly,
 * so the producer side has to set it. We wire onnodedragstop on the
 * BPMN view and hit-test against pool bounds when a lane drops.
 */

const UNIFIED = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/UnifiedCanvas.svelte'),
	'utf-8',
);
const SHELL = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/bpmn/BpmnAuthoringShell.svelte'),
	'utf-8',
);

describe('Lane-on-pool parentId wiring (#5, v5.4.0)', () => {
	it('UnifiedCanvas exposes an onnodedragstop prop wired to <SvelteFlow>', () => {
		expect(UNIFIED).toMatch(/onnodedragstop\?:/);
		expect(UNIFIED).toMatch(/<SvelteFlow[\s\S]*?onnodedragstop=/);
	});

	it('BpmnAuthoringShell implements drop-on-pool parent assignment', () => {
		// The shell owns the BPMN-specific hit-test (pool / lane semantics
		// don't apply on other notations).
		expect(SHELL).toMatch(/handleBpmnDragStop/);
		expect(SHELL).toMatch(/onnodedragstop=\{handleBpmnDragStop\}/);
		const fn = SHELL.match(/function handleBpmnDragStop[\s\S]*?\n\t\}/)?.[0] ?? '';
		expect(fn).toMatch(/parentId/);
		expect(fn).toMatch(/pool/);
		expect(fn).toMatch(/lane/);
	});
});
