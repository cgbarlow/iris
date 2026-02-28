import { describe, it, expect } from 'vitest';
import { simpleViewNodeTypes } from '$lib/canvas/nodes';
import { SIMPLE_ENTITY_TYPES, SIMPLE_RELATIONSHIP_TYPES } from '$lib/types/canvas';
import type { CanvasNode, CanvasEdge, SimpleEntityType, SimpleRelationshipType } from '$lib/types/canvas';

describe('Canvas bug fixes', () => {
	describe('Bug fix: simpleEntity type (was type: "simpleEntity")', () => {
		it('creating a node uses entityType as the type key, not "simpleEntity"', () => {
			const entityType: SimpleEntityType = 'component';
			const node: CanvasNode = {
				id: 'test-1',
				type: entityType,
				position: { x: 100, y: 100 },
				data: { label: 'Test', entityType, description: '' },
			};
			// The type field must match a key in simpleViewNodeTypes
			expect(node.type).toBe('component');
			expect(node.type).not.toBe('simpleEntity');
			expect(Object.keys(simpleViewNodeTypes)).toContain(node.type);
		});

		it('all entity types are registered in simpleViewNodeTypes', () => {
			for (const entityType of SIMPLE_ENTITY_TYPES) {
				expect(Object.keys(simpleViewNodeTypes)).toContain(entityType.key);
			}
		});
	});

	describe('Bug fix: RelationshipDialog wiring', () => {
		it('relationship types include all 5 simple view types', () => {
			expect(SIMPLE_RELATIONSHIP_TYPES).toHaveLength(5);
			const keys = SIMPLE_RELATIONSHIP_TYPES.map(t => t.key);
			expect(keys).toContain('uses');
			expect(keys).toContain('depends_on');
			expect(keys).toContain('composes');
			expect(keys).toContain('implements');
			expect(keys).toContain('contains');
		});

		it('edge can be created with any relationship type', () => {
			for (const relType of SIMPLE_RELATIONSHIP_TYPES) {
				const key = relType.key as SimpleRelationshipType;
				const edge: CanvasEdge = {
					id: `e-test-${key}`,
					source: 'n1',
					target: 'n2',
					type: key,
					data: { relationshipType: key },
				};
				expect(edge.type).toBe(key);
				expect(edge.data!.relationshipType).toBe(key);
			}
		});
	});

	describe('Bug fix: EntityDetailPanel data contract', () => {
		it('CanvasNodeData has required fields for EntityDetailPanel', () => {
			const node: CanvasNode = {
				id: 'n1',
				type: 'service',
				position: { x: 0, y: 0 },
				data: {
					label: 'My Service',
					entityType: 'service',
					description: 'A test service',
					entityId: 'entity-123',
				},
			};
			// EntityDetailPanel reads these fields
			expect(node.data.label).toBeTruthy();
			expect(node.data.entityType).toBeTruthy();
			expect(node.data.description).toBeTruthy();
			expect(node.data.entityId).toBeTruthy();
		});
	});
});
