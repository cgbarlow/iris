import { describe, it, expect } from 'vitest';
import {
	ARCHIMATE_ENTITY_TYPES,
	ARCHIMATE_RELATIONSHIP_TYPES,
	type ArchimateEntityType,
	type ArchimateLayer,
} from '$lib/types/canvas';

describe('ArchiMate Full View types', () => {
	it('defines all 11 ArchiMate entity types', () => {
		expect(ARCHIMATE_ENTITY_TYPES).toHaveLength(11);
	});

	it('defines all 8 ArchiMate relationship types', () => {
		expect(ARCHIMATE_RELATIONSHIP_TYPES).toHaveLength(8);
	});

	it('covers all 3 ArchiMate layers', () => {
		const layers = new Set(ARCHIMATE_ENTITY_TYPES.map((t) => t.layer));
		expect(layers).toContain('business');
		expect(layers).toContain('application');
		expect(layers).toContain('technology');
	});

	it('business layer has 5 types', () => {
		const business = ARCHIMATE_ENTITY_TYPES.filter((t) => t.layer === 'business');
		expect(business).toHaveLength(5);
	});

	it('application layer has 3 types', () => {
		const app = ARCHIMATE_ENTITY_TYPES.filter((t) => t.layer === 'application');
		expect(app).toHaveLength(3);
	});

	it('technology layer has 3 types', () => {
		const tech = ARCHIMATE_ENTITY_TYPES.filter((t) => t.layer === 'technology');
		expect(tech).toHaveLength(3);
	});

	it('each entity type has label, icon, layer, and description', () => {
		for (const t of ARCHIMATE_ENTITY_TYPES) {
			expect(t.label).toBeTruthy();
			expect(t.icon).toBeTruthy();
			expect(t.layer).toBeTruthy();
			expect(t.description).toBeTruthy();
		}
	});

	it('each relationship type has label and description', () => {
		for (const t of ARCHIMATE_RELATIONSHIP_TYPES) {
			expect(t.label).toBeTruthy();
			expect(t.description).toBeTruthy();
		}
	});
});
