import { describe, it, expect } from 'vitest';
import {
	UML_ENTITY_TYPES,
	UML_RELATIONSHIP_TYPES,
	type UmlEntityType,
	type UmlRelationshipType,
} from '$lib/types/canvas';

describe('UML Full View types', () => {
	it('defines all 11 UML entity types', () => {
		expect(UML_ENTITY_TYPES).toHaveLength(11);
		const keys = UML_ENTITY_TYPES.map((t) => t.key);
		expect(keys).toContain('class');
		expect(keys).toContain('object');
		expect(keys).toContain('use_case');
		expect(keys).toContain('state');
		expect(keys).toContain('activity');
		expect(keys).toContain('node');
		expect(keys).toContain('interface_uml');
		expect(keys).toContain('enumeration');
		expect(keys).toContain('abstract_class');
		expect(keys).toContain('component_uml');
		expect(keys).toContain('package_uml');
	});

	it('defines all 7 UML relationship types', () => {
		expect(UML_RELATIONSHIP_TYPES).toHaveLength(7);
		const keys = UML_RELATIONSHIP_TYPES.map((t) => t.key);
		expect(keys).toContain('association');
		expect(keys).toContain('aggregation');
		expect(keys).toContain('composition');
		expect(keys).toContain('dependency');
		expect(keys).toContain('realization');
		expect(keys).toContain('generalization');
	});

	it('each UML entity type has label, icon, and description', () => {
		for (const t of UML_ENTITY_TYPES) {
			expect(t.label).toBeTruthy();
			expect(t.icon).toBeTruthy();
			expect(t.description).toBeTruthy();
		}
	});

	it('each UML relationship type has label and description', () => {
		for (const t of UML_RELATIONSHIP_TYPES) {
			expect(t.label).toBeTruthy();
			expect(t.description).toBeTruthy();
		}
	});
});
