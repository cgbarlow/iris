import { describe, it, expect } from 'vitest';
import { umlNodeTypes } from '$lib/canvas/uml/nodes';
import { umlEdgeTypes } from '$lib/canvas/uml/edges';
import { archimateNodeTypes } from '$lib/canvas/archimate/nodes';
import { archimateEdgeTypes } from '$lib/canvas/archimate/edges';
import { UML_ENTITY_TYPES, UML_RELATIONSHIP_TYPES, ARCHIMATE_ENTITY_TYPES, ARCHIMATE_RELATIONSHIP_TYPES } from '$lib/types/canvas';

describe('FullViewCanvas type registries', () => {
	it('UML node types match UML entity type keys', () => {
		const registryKeys = Object.keys(umlNodeTypes);
		const typeKeys = UML_ENTITY_TYPES.map(t => t.key);
		for (const key of typeKeys) {
			expect(registryKeys).toContain(key);
		}
	});

	it('UML edge types match UML relationship type keys', () => {
		const registryKeys = Object.keys(umlEdgeTypes);
		const typeKeys = UML_RELATIONSHIP_TYPES.map(t => t.key);
		for (const key of typeKeys) {
			expect(registryKeys).toContain(key);
		}
	});

	it('ArchiMate node types match ArchiMate entity type keys', () => {
		const registryKeys = Object.keys(archimateNodeTypes);
		const typeKeys = ARCHIMATE_ENTITY_TYPES.map(t => t.key);
		for (const key of typeKeys) {
			expect(registryKeys).toContain(key);
		}
	});

	it('ArchiMate edge types match ArchiMate relationship type keys', () => {
		const registryKeys = Object.keys(archimateEdgeTypes);
		const typeKeys = ARCHIMATE_RELATIONSHIP_TYPES.map(t => t.key);
		for (const key of typeKeys) {
			expect(registryKeys).toContain(key);
		}
	});

	it('UML has 6 node types', () => {
		expect(Object.keys(umlNodeTypes)).toHaveLength(6);
	});

	it('UML has 6 edge types', () => {
		expect(Object.keys(umlEdgeTypes)).toHaveLength(6);
	});

	it('ArchiMate has 11 node types', () => {
		expect(Object.keys(archimateNodeTypes)).toHaveLength(11);
	});

	it('ArchiMate has 8 edge types', () => {
		expect(Object.keys(archimateEdgeTypes)).toHaveLength(8);
	});
});

describe('Model type to canvas type mapping', () => {
	function getCanvasType(modelType: string): string {
		if (modelType === 'sequence') return 'sequence';
		if (modelType === 'uml') return 'uml';
		if (modelType === 'archimate') return 'archimate';
		return 'simple';
	}

	it('maps simple to simple', () => {
		expect(getCanvasType('simple')).toBe('simple');
	});

	it('maps component to simple', () => {
		expect(getCanvasType('component')).toBe('simple');
	});

	it('maps sequence to sequence', () => {
		expect(getCanvasType('sequence')).toBe('sequence');
	});

	it('maps uml to uml', () => {
		expect(getCanvasType('uml')).toBe('uml');
	});

	it('maps archimate to archimate', () => {
		expect(getCanvasType('archimate')).toBe('archimate');
	});
});
