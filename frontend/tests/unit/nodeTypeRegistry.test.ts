import { describe, it, expect } from 'vitest';
import { simpleViewNodeTypes } from '$lib/canvas/nodes';
import { simpleViewEdgeTypes } from '$lib/canvas/edges';
import { SIMPLE_ENTITY_TYPES, SIMPLE_RELATIONSHIP_TYPES } from '$lib/types/canvas';

describe('Node type registry alignment', () => {
	it('every Simple View entity type key is registered in simpleViewNodeTypes', () => {
		const registryKeys = Object.keys(simpleViewNodeTypes);
		for (const entityType of SIMPLE_ENTITY_TYPES) {
			expect(registryKeys).toContain(entityType.key);
		}
	});

	it('every Simple View relationship type key is registered in simpleViewEdgeTypes', () => {
		const registryKeys = Object.keys(simpleViewEdgeTypes);
		for (const relType of SIMPLE_RELATIONSHIP_TYPES) {
			expect(registryKeys).toContain(relType.key);
		}
	});

	it('no unregistered node type exists (bug fix verification)', () => {
		// This test verifies the bug fix: type should be entityType, NOT "simpleEntity"
		const registryKeys = Object.keys(simpleViewNodeTypes);
		expect(registryKeys).not.toContain('simpleEntity');
	});

	it('simpleViewNodeTypes has exactly 7 entries', () => {
		expect(Object.keys(simpleViewNodeTypes)).toHaveLength(7);
	});

	it('simpleViewEdgeTypes has exactly 5 entries', () => {
		expect(Object.keys(simpleViewEdgeTypes)).toHaveLength(5);
	});
});
