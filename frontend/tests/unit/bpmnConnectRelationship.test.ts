// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.1 — issue #46 item #10: When a user drags a connection between
 * two BPMN nodes, the BpmnAuthoringShell must POST a real
 * `/api/relationships` record so the backing Element shows the
 * relationship under /elements/<id>'s Relationships panel — matching
 * the page-level `handleRelationshipSave` flow other notations use.
 */

const SRC = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/bpmn/BpmnAuthoringShell.svelte'),
	'utf-8',
);

describe('BPMN connect → relationship (v5.4.1, issue #46 item #10)', () => {
	it('<UnifiedCanvas> in BpmnAuthoringShell wires onconnectnodes to a local handler', () => {
		// Match the <UnifiedCanvas …/> block.
		const ucMatch = SRC.match(/<UnifiedCanvas\b[^/]*?\/>/s);
		expect(ucMatch, '<UnifiedCanvas /> in shell').not.toBeNull();
		const block = ucMatch![0];
		expect(block).toMatch(/onconnectnodes\s*=\s*\{/);
	});

	it('the connect handler POSTs /api/relationships with sequence_flow', () => {
		// Find the connect handler — by convention `handleBpmnConnect` or
		// `handleConnect`. Match its body.
		const fnMatch = SRC.match(/(?:async\s+)?function\s+(?:handleBpmnConnect|handleConnect)\s*\([^)]*\)\s*\{[\s\S]*?\n\t\}\n/);
		expect(fnMatch, 'connect handler in shell').not.toBeNull();
		const fn = fnMatch![0];

		expect(fn, 'POSTs /api/relationships').toMatch(/['"`]\/api\/relationships['"`]/);
		expect(fn, 'method: POST').toMatch(/method\s*:\s*['"]POST['"]/);
		expect(fn, 'sequence_flow relationship type').toMatch(/sequence_flow/);
		// Must add an edge with type sequence_flow to canvasEdges.
		expect(fn, 'adds an edge with type sequence_flow').toMatch(/type\s*:\s*['"]sequence_flow['"]/);
		expect(fn, 'mutates canvasEdges').toMatch(/canvasEdges\s*=\s*\[/);
	});
});
