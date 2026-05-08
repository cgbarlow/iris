// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * BPMN-08 (issue #69 ledger): when `/api/elements` POST fails,
 * createBpmnElement returns null and the caller MUST NOT add a node to
 * canvasNodes. Otherwise we'd have an orphan canvas node with no entityId,
 * which then breaks every downstream feature (search, knowledge graph,
 * /elements/<id>, drag-connect persistence).
 *
 * Every node-creation path must:
 *   1. Call createBpmnElement and await its result.
 *   2. Bail out with `if (!element) return` (or equivalent) before any
 *      mutation of canvasNodes/canvasEdges.
 */

const SRC = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/bpmn/BpmnAuthoringShell.svelte'),
	'utf-8',
);

const NODE_CREATION_FNS = [
	'createNode',
	'handleEventVariant',
	'appendBpmnNodeWithEdge',
];

describe('BPMN-08 (issue #69): node-creation paths bail on /api/elements failure', () => {
	for (const name of NODE_CREATION_FNS) {
		it(`${name} bails out before mutating canvasNodes when createBpmnElement returns null`, () => {
			const fnMatch = SRC.match(new RegExp(`async\\s+function\\s+${name}\\s*\\([^)]*\\)\\s*\\{[\\s\\S]*?\\n\\t\\}`));
			expect(fnMatch, `${name} handler`).not.toBeNull();
			const fn = fnMatch![0];

			expect(fn, 'awaits createBpmnElement').toMatch(/await\s+createBpmnElement\s*\(/);
			// Find the position of the createBpmnElement call and the first
			// canvasNodes mutation after it.
			const elemIdx = fn.search(/await\s+createBpmnElement\s*\(/);
			const guardIdx = fn.search(/if\s*\(\s*!\s*element\s*\)\s*return/);
			const mutateIdx = fn.search(/canvasNodes\s*=\s*\[/);

			expect(elemIdx, 'createBpmnElement called').toBeGreaterThan(-1);
			expect(guardIdx, '`if (!element) return` guard present').toBeGreaterThan(elemIdx);
			if (mutateIdx > -1) {
				expect(mutateIdx, 'canvasNodes mutation comes AFTER the guard')
					.toBeGreaterThan(guardIdx);
			}
		});
	}

	it('createBpmnElement returns null on caught error and surfaces a toast', () => {
		const fnMatch = SRC.match(/async\s+function\s+createBpmnElement\s*\([^)]*\)[\s\S]*?\n\t\}/);
		expect(fnMatch, 'createBpmnElement helper').not.toBeNull();
		const fn = fnMatch![0];
		expect(fn, 'returns null on catch').toMatch(/return\s+null/);
		expect(fn, 'sets toastMessage on failure').toMatch(/toastMessage\s*=/);
		expect(fn, 'logs to console.error for diagnostics').toMatch(/console\.error/);
	});
});
