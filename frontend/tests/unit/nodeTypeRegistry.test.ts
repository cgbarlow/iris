import { describe, it, expect } from 'vitest';
import { simpleViewNodeTypes } from '$lib/canvas/nodes';
import { simpleViewEdgeTypes } from '$lib/canvas/edges';
import { unifiedNodeTypes, unifiedEdgeTypes, TYPE_EQUIVALENCES } from '$lib/canvas/registry';
import {
	SIMPLE_ENTITY_TYPES,
	SIMPLE_RELATIONSHIP_TYPES,
	UML_ENTITY_TYPES,
	UML_RELATIONSHIP_TYPES,
	ARCHIMATE_ENTITY_TYPES,
	ARCHIMATE_RELATIONSHIP_TYPES,
} from '$lib/types/canvas';

describe('Legacy node type registry alignment', () => {
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

	it('simpleViewNodeTypes has exactly 10 entries', () => {
		expect(Object.keys(simpleViewNodeTypes)).toHaveLength(10);
	});

	it('simpleViewEdgeTypes has exactly 7 entries', () => {
		expect(Object.keys(simpleViewEdgeTypes)).toHaveLength(7);
	});
});

describe('Unified registry (ADR-068)', () => {
	it('every Simple View entity type is in unified node registry', () => {
		for (const entityType of SIMPLE_ENTITY_TYPES) {
			expect(unifiedNodeTypes).toHaveProperty(entityType.key);
		}
	});

	it('every UML entity type is in unified node registry', () => {
		for (const entityType of UML_ENTITY_TYPES) {
			expect(unifiedNodeTypes).toHaveProperty(entityType.key);
		}
	});

	it('every ArchiMate entity type is in unified node registry', () => {
		for (const entityType of ARCHIMATE_ENTITY_TYPES) {
			expect(unifiedNodeTypes).toHaveProperty(entityType.key);
		}
	});

	it('every Simple relationship type is in unified edge registry', () => {
		for (const relType of SIMPLE_RELATIONSHIP_TYPES) {
			expect(unifiedEdgeTypes).toHaveProperty(relType.key);
		}
	});

	it('every UML relationship type is in unified edge registry', () => {
		for (const relType of UML_RELATIONSHIP_TYPES) {
			expect(unifiedEdgeTypes).toHaveProperty(relType.key);
		}
	});

	it('every ArchiMate relationship type is in unified edge registry', () => {
		for (const relType of ARCHIMATE_RELATIONSHIP_TYPES) {
			expect(unifiedEdgeTypes).toHaveProperty(relType.key);
		}
	});

	it('universal types (note, boundary, modelref) are in unified registry', () => {
		expect(unifiedNodeTypes).toHaveProperty('note');
		expect(unifiedNodeTypes).toHaveProperty('boundary');
		expect(unifiedNodeTypes).toHaveProperty('modelref');
	});

	it('special edge types (note_link, self_loop) are in unified registry', () => {
		expect(unifiedEdgeTypes).toHaveProperty('note_link');
		expect(unifiedEdgeTypes).toHaveProperty('self_loop');
	});

	it('all unified node types map to the same DynamicNode component', () => {
		const components = new Set(Object.values(unifiedNodeTypes));
		expect(components.size).toBe(1);
	});

	it('all unified edge types map to the same DynamicEdge component', () => {
		const components = new Set(Object.values(unifiedEdgeTypes));
		expect(components.size).toBe(1);
	});
});

describe('Type equivalence map (ADR-068)', () => {
	it('component maps across simple, uml, and archimate', () => {
		expect(TYPE_EQUIVALENCES.component).toEqual({
			simple: 'component',
			uml: 'component_uml',
			archimate: 'application_component',
		});
	});

	it('actor maps across simple and archimate', () => {
		expect(TYPE_EQUIVALENCES.actor).toEqual({
			simple: 'actor',
			archimate: 'business_actor',
		});
	});

	it('interface maps across simple, uml, and archimate', () => {
		expect(TYPE_EQUIVALENCES.interface).toEqual({
			simple: 'interface',
			uml: 'interface_uml',
			archimate: 'application_interface',
		});
	});

	it('all equivalence target types exist in unified registry', () => {
		for (const [, mappings] of Object.entries(TYPE_EQUIVALENCES)) {
			for (const [, typeKey] of Object.entries(mappings)) {
				expect(unifiedNodeTypes).toHaveProperty(typeKey as string);
			}
		}
	});
});
