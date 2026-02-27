import { describe, it, expect } from 'vitest';
import {
	SIMPLE_ENTITY_TYPES,
	SIMPLE_RELATIONSHIP_TYPES,
	type SimpleEntityType,
	type SimpleRelationshipType,
} from '$lib/types/canvas';

describe('Canvas types', () => {
	it('defines all 7 Simple View entity types', () => {
		expect(SIMPLE_ENTITY_TYPES).toHaveLength(7);
		const keys = SIMPLE_ENTITY_TYPES.map((t) => t.key);
		expect(keys).toContain('component');
		expect(keys).toContain('service');
		expect(keys).toContain('interface');
		expect(keys).toContain('package');
		expect(keys).toContain('actor');
		expect(keys).toContain('database');
		expect(keys).toContain('queue');
	});

	it('defines all 5 Simple View relationship types', () => {
		expect(SIMPLE_RELATIONSHIP_TYPES).toHaveLength(5);
		const keys = SIMPLE_RELATIONSHIP_TYPES.map((t) => t.key);
		expect(keys).toContain('uses');
		expect(keys).toContain('depends_on');
		expect(keys).toContain('composes');
		expect(keys).toContain('implements');
		expect(keys).toContain('contains');
	});

	it('each entity type has label, icon, and description', () => {
		for (const t of SIMPLE_ENTITY_TYPES) {
			expect(t.label).toBeTruthy();
			expect(t.icon).toBeTruthy();
			expect(t.description).toBeTruthy();
		}
	});

	it('each relationship type has label and description', () => {
		for (const t of SIMPLE_RELATIONSHIP_TYPES) {
			expect(t.label).toBeTruthy();
			expect(t.description).toBeTruthy();
		}
	});

	it('entity type keys are valid SimpleEntityType', () => {
		const validKeys: SimpleEntityType[] = [
			'component',
			'service',
			'interface',
			'package',
			'actor',
			'database',
			'queue',
		];
		for (const t of SIMPLE_ENTITY_TYPES) {
			expect(validKeys).toContain(t.key);
		}
	});

	it('relationship type keys are valid SimpleRelationshipType', () => {
		const validKeys: SimpleRelationshipType[] = [
			'uses',
			'depends_on',
			'composes',
			'implements',
			'contains',
		];
		for (const t of SIMPLE_RELATIONSHIP_TYPES) {
			expect(validKeys).toContain(t.key);
		}
	});
});
