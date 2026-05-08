// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.1 (#46 item #10) → v5.6.2 (issue #69): When a user drags a connection
 * between two BPMN nodes, the BpmnAuthoringShell must POST a real
 * `/api/relationships` record so the backing Element shows the relationship
 * under /elements/<id>'s Relationships panel — matching the page-level
 * `handleRelationshipSave` flow other notations use.
 *
 * v5.6.2 (issue #69) shifts edge addition to UnifiedCanvas (which calls
 * `patchConnectedEdgeType` after xyflow's auto-add to fix the missing-type
 * gap). The shell handler now patches the existing edge with the resulting
 * `relationshipId` rather than appending a duplicate.
 */

const SRC = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/bpmn/BpmnAuthoringShell.svelte'),
	'utf-8',
);

describe('BPMN connect → relationship (v5.4.1 #46/10 + v5.6.2 #69)', () => {
	it('<UnifiedCanvas> in BpmnAuthoringShell wires onconnectnodes to a local handler', () => {
		// Anchor on `bind:nodes={canvasNodes}` so prose mentions of
		// "<UnifiedCanvas>" in nearby docstrings don't capture first.
		const ucMatch = SRC.match(/<UnifiedCanvas\b[\s\S]*?bind:nodes=\{canvasNodes\}[\s\S]*?\/>/);
		expect(ucMatch, '<UnifiedCanvas /> in shell').not.toBeNull();
		const block = ucMatch![0];
		expect(block).toMatch(/onconnectnodes\s*=\s*\{/);
	});

	it('the connect handler POSTs /api/relationships with sequence_flow', () => {
		const fnMatch = SRC.match(/async\s+function\s+handleBpmnConnect\s*\([^)]*\)\s*\{[\s\S]*?\n\t\}/);
		expect(fnMatch, 'handleBpmnConnect handler in shell').not.toBeNull();
		const fn = fnMatch![0];

		expect(fn, 'POSTs /api/relationships').toMatch(/['"`]\/api\/relationships['"`]/);
		expect(fn, 'method: POST').toMatch(/method\s*:\s*['"]POST['"]/);
		expect(fn, 'sequence_flow relationship type').toMatch(/sequence_flow/);
	});

	it('handler patches the existing edge with relationshipId rather than appending a duplicate (v5.6.2 #69)', () => {
		const fnMatch = SRC.match(/async\s+function\s+handleBpmnConnect\s*\([^)]*\)\s*\{[\s\S]*?\n\t\}/);
		expect(fnMatch, 'handleBpmnConnect handler in shell').not.toBeNull();
		const fn = fnMatch![0];

		// Patches via .map(...) over canvasEdges, sets relationshipId on the
		// matching one. Must NOT contain `canvasEdges = [...canvasEdges,` (that
		// was the v5.4.1 shape that double-added edges once UnifiedCanvas owned
		// the auto-add).
		expect(fn, 'no longer appends a fresh edge').not.toMatch(/canvasEdges\s*=\s*\[\s*\.\.\.canvasEdges\s*,/);
		expect(fn, 'maps over canvasEdges').toMatch(/canvasEdges\s*=\s*canvasEdges\.map/);
		expect(fn, 'attaches relationshipId').toMatch(/relationshipId\s*:\s*rel\.id/);
	});
});
