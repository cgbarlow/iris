// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.6.2 (issue #69 follow-up to BPMN-02): the v5.4.1 fix routed drag-handle
 * connections through `handleBpmnConnect` to POST `/api/relationships`. But
 * the ContextPad append actions (`append_task` / `append_gateway` /
 * `append_end_event`) and CommandPalette append (`A` hotkey or modal "append"
 * mode) also create new node + edge pairs and silently skipped the
 * relationship POST. So `/elements/<id>`'s Relationships panel was empty for
 * append-created edges, identical to the pre-v5.4.1 bug.
 *
 * Shared helper `appendBpmnNodeWithEdge` is the single source of truth for
 * "append a BPMN node + sequence_flow edge + POST /api/relationships". Both
 * `appendBpmn` (called by ContextPad actions) and `handleCmdPick('append')`
 * (CommandPalette) route through it (DRY per protocol #13).
 */

const SRC = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/bpmn/BpmnAuthoringShell.svelte'),
	'utf-8',
);

describe('BPMN append → /api/relationships (v5.6.2 issue #69 follow-up to BPMN-02)', () => {
	it('appendBpmnNodeWithEdge is the shared helper that POSTs /api/relationships', () => {
		const fnMatch = SRC.match(/async\s+function\s+appendBpmnNodeWithEdge\s*\([^)]*\)\s*\{[\s\S]*?\n\t\}/);
		expect(fnMatch, 'appendBpmnNodeWithEdge helper').not.toBeNull();
		const fn = fnMatch![0];
		expect(fn, 'POSTs /api/relationships').toMatch(/['"`]\/api\/relationships['"`]/);
		expect(fn, 'method: POST').toMatch(/method\s*:\s*['"]POST['"]/);
		expect(fn, 'sequence_flow relationship type').toMatch(/sequence_flow/);
		expect(fn, 'gates POST on both endpoints having entityId')
			.toMatch(/sourceEntityId\s*&&\s*targetEntityId/);
	});

	it('appendBpmn delegates to the shared helper (DRY)', () => {
		const fnMatch = SRC.match(/async\s+function\s+appendBpmn\s*\([^)]*\)\s*\{[\s\S]*?\n\t\}/);
		expect(fnMatch, 'appendBpmn handler').not.toBeNull();
		const fn = fnMatch![0];
		expect(fn, 'calls appendBpmnNodeWithEdge').toMatch(/appendBpmnNodeWithEdge\s*\(/);
	});

	it('handleCmdPick (append branch) delegates to the shared helper', () => {
		// Find the body of handleCmdPick.
		const fnMatch = SRC.match(/async\s+function\s+handleCmdPick\s*\([^)]*\)\s*\{[\s\S]*?\n\t\}/);
		expect(fnMatch, 'handleCmdPick handler').not.toBeNull();
		const fn = fnMatch![0];
		// Append branch must call the helper rather than re-implementing.
		expect(fn, 'append branch routes through appendBpmnNodeWithEdge')
			.toMatch(/['"]append['"][\s\S]*?appendBpmnNodeWithEdge\s*\(/);
	});

	it('helper attaches relationshipId to the canvas edge on success', () => {
		const fnMatch = SRC.match(/async\s+function\s+appendBpmnNodeWithEdge\s*\([^)]*\)\s*\{[\s\S]*?\n\t\}/);
		const fn = fnMatch![0];
		// On successful POST, the edge data must carry the resulting
		// relationshipId so /elements/<id>'s Relationships panel can resolve.
		expect(fn, 'edge data carries relationshipId').toMatch(/relationshipId/);
	});
});
