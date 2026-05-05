// @ts-nocheck — Node fs/path imports.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.0 (issue cluster): v5.2.0 hard-coded `width: 200` for every BPMN
 * entity in `makeBpmnNode`, so events (visually 56×56) had a 200px-wide
 * bounding box. This pushed the ContextPad far to the right of the
 * actual circle. Per-type dimensions fix the box → match the visual.
 */

const SHELL = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/bpmn/BpmnAuthoringShell.svelte'),
	'utf-8',
);

describe('ProblemsPanel scroll containment (#1, v5.4.0)', () => {
	it('.bpmn-shell__problems lets its child scroll instead of bubbling to the page', () => {
		// Before v5.4.0 this wrapper had `overflow: hidden`, blocking the
		// inner ProblemsPanel list's `overflow-y: auto` so the page got the
		// scrollbar instead of the panel.
		const block = SHELL.match(/\.bpmn-shell__problems\s*\{[\s\S]*?\}/)?.[0] ?? '';
		expect(block).not.toMatch(/overflow:\s*hidden/);
		expect(block).toMatch(/overflow-y:\s*auto|overflow:\s*auto/);
	});
});

describe('BPMN per-entity-type node sizing (issue cluster, v5.4.0)', () => {
	it('declares a BPMN_NODE_DIMENSIONS lookup', () => {
		expect(SHELL).toMatch(/BPMN_NODE_DIMENSIONS\s*[:=]/);
	});

	it('events are 56×56 (matches the 56×56 circle in BpmnRenderer.css)', () => {
		const slice = SHELL.match(/event_start[\s\S]{0,80}/)?.[0] ?? '';
		expect(slice).toMatch(/56/);
	});

	it('gateways are 56×56', () => {
		const slice = SHELL.match(/gateway[\s\S]{0,80}/)?.[0] ?? '';
		expect(slice).toMatch(/56/);
	});

	it('pools are wide containers (≥240px)', () => {
		const slice = SHELL.match(/\bpool\s*:\s*\{[\s\S]{0,80}/)?.[0] ?? '';
		const m = slice.match(/width\s*:\s*(\d+)/);
		expect(m).toBeTruthy();
		expect(parseInt(m![1], 10)).toBeGreaterThanOrEqual(240);
	});

	it('makeBpmnNode reads from the dimensions lookup (no hard-coded 200)', () => {
		// The function signature must consult BPMN_NODE_DIMENSIONS — directly
		// or via a derived helper — for both width and (where applicable) height.
		const fn = SHELL.match(/function\s+makeBpmnNode[\s\S]*?\n\t\}/)?.[0] ?? '';
		expect(fn).toMatch(/BPMN_NODE_DIMENSIONS/);
	});
});
