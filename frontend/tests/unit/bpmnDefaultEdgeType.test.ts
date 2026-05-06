// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.1 — issue #46 item #9: Pre-fix, the UnifiedCanvas
 * `defaultEdgeType` $derived had cases for uml + archimate + default
 * 'uses' but NO case for 'bpmn'. So a handle-drag in a BPMN view
 * created an edge with type='uses', and the validator's
 * "no outgoing sequence flow" rule (filters by type==='sequence_flow')
 * correctly reported the source had none.
 */

const SRC = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/UnifiedCanvas.svelte'),
	'utf-8',
);

describe('UnifiedCanvas defaultEdgeType (v5.4.1, issue #46 item #9)', () => {
	it('returns "sequence_flow" when notation === "bpmn"', () => {
		// Locate the defaultEdgeType $derived block.
		const match = SRC.match(/defaultEdgeType\s*=\s*\$derived\s*\(([\s\S]*?)\);/);
		expect(match, 'defaultEdgeType $derived found').not.toBeNull();
		const body = match![1];

		// Must contain a notation === 'bpmn' arm returning 'sequence_flow'.
		expect(body).toMatch(/notation\s*===\s*['"]bpmn['"][\s\S]*?['"]sequence_flow['"]/);
	});
});
