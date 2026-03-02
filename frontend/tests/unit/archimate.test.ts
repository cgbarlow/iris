import { describe, it, expect } from 'vitest';
import {
	ARCHIMATE_ENTITY_TYPES,
	ARCHIMATE_RELATIONSHIP_TYPES,
	type ArchimateEntityType,
	type ArchimateLayer,
} from '$lib/types/canvas';

describe('ArchiMate Full View types', () => {
	it('defines all 45 ArchiMate entity types', () => {
		expect(ARCHIMATE_ENTITY_TYPES).toHaveLength(45);
	});

	it('defines all 11 ArchiMate relationship types', () => {
		expect(ARCHIMATE_RELATIONSHIP_TYPES).toHaveLength(11);
	});

	it('covers all 6 ArchiMate layers', () => {
		const layers = new Set(ARCHIMATE_ENTITY_TYPES.map((t) => t.layer));
		expect(layers).toContain('business');
		expect(layers).toContain('application');
		expect(layers).toContain('technology');
		expect(layers).toContain('motivation');
		expect(layers).toContain('strategy');
		expect(layers).toContain('implementation_migration');
	});

	it('business layer has 10 types', () => {
		const business = ARCHIMATE_ENTITY_TYPES.filter((t) => t.layer === 'business');
		expect(business).toHaveLength(10);
	});

	it('application layer has 8 types', () => {
		const app = ARCHIMATE_ENTITY_TYPES.filter((t) => t.layer === 'application');
		expect(app).toHaveLength(8);
	});

	it('technology layer has 10 types', () => {
		const tech = ARCHIMATE_ENTITY_TYPES.filter((t) => t.layer === 'technology');
		expect(tech).toHaveLength(10);
	});

	it('motivation layer has 8 types', () => {
		const motivation = ARCHIMATE_ENTITY_TYPES.filter((t) => t.layer === 'motivation');
		expect(motivation).toHaveLength(8);
	});

	it('strategy layer has 4 types', () => {
		const strategy = ARCHIMATE_ENTITY_TYPES.filter((t) => t.layer === 'strategy');
		expect(strategy).toHaveLength(4);
	});

	it('implementation_migration layer has 5 types', () => {
		const impl = ARCHIMATE_ENTITY_TYPES.filter((t) => t.layer === 'implementation_migration');
		expect(impl).toHaveLength(5);
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
