import { describe, it, expect } from 'vitest';
import {
	SIMPLE_ENTITY_TYPES,
	SIMPLE_RELATIONSHIP_TYPES,
	UML_ENTITY_TYPES,
	UML_RELATIONSHIP_TYPES,
	ARCHIMATE_ENTITY_TYPES,
	ARCHIMATE_RELATIONSHIP_TYPES,
} from '$lib/types/canvas';
import { createCanvasNode, createCanvasEdge, nodesToPlacements } from '$lib/canvas/canvasService';

/**
 * Performance tests for canvas operations at scale.
 * Verifies that core operations remain fast with large datasets.
 */

function generateNodes(count: number) {
	const nodes = [];
	for (let i = 0; i < count; i++) {
		nodes.push(
			createCanvasNode(`Node ${i}`, 'component', `Description ${i}`, {
				x: (i % 20) * 200,
				y: Math.floor(i / 20) * 150,
			}),
		);
	}
	return nodes;
}

function generateEdges(nodes: ReturnType<typeof createCanvasNode>[], edgeCount: number) {
	const edges = [];
	for (let i = 0; i < edgeCount && i < nodes.length - 1; i++) {
		edges.push(createCanvasEdge(nodes[i].id, nodes[i + 1].id, 'uses'));
	}
	return edges;
}

describe('Canvas creation performance', () => {
	it('creates 500 nodes in under 100ms', () => {
		const start = performance.now();
		const nodes = generateNodes(500);
		const elapsed = performance.now() - start;

		expect(nodes).toHaveLength(500);
		expect(elapsed).toBeLessThan(100);
	});

	it('creates 1000 nodes in under 200ms', () => {
		const start = performance.now();
		const nodes = generateNodes(1000);
		const elapsed = performance.now() - start;

		expect(nodes).toHaveLength(1000);
		expect(elapsed).toBeLessThan(200);
	});

	it('creates 500 edges in under 100ms', () => {
		const nodes = generateNodes(501);
		const start = performance.now();
		const edges = generateEdges(nodes, 500);
		const elapsed = performance.now() - start;

		expect(edges).toHaveLength(500);
		expect(elapsed).toBeLessThan(100);
	});
});

describe('Canvas serialization performance', () => {
	it('serializes 500 nodes to placements in under 50ms', () => {
		const nodes = generateNodes(500);
		const start = performance.now();
		const placements = nodesToPlacements(nodes);
		const elapsed = performance.now() - start;

		expect(placements).toHaveLength(500);
		expect(elapsed).toBeLessThan(50);
	});

	it('serializes 1000 nodes to placements in under 100ms', () => {
		const nodes = generateNodes(1000);
		const start = performance.now();
		const placements = nodesToPlacements(nodes);
		const elapsed = performance.now() - start;

		expect(placements).toHaveLength(1000);
		expect(elapsed).toBeLessThan(100);
	});
});

describe('Client-side filtering performance', () => {
	it('filters 5000 entities by text search in under 50ms', () => {
		const entities = Array.from({ length: 5000 }, (_, i) => ({
			id: `entity-${i}`,
			name: `Entity ${i} ${i % 3 === 0 ? 'service' : 'component'}`,
			entity_type: i % 7 === 0 ? 'service' : 'component',
			description: `Description for entity ${i}`,
		}));

		const query = 'service';
		const start = performance.now();
		const filtered = entities.filter(
			(e) =>
				e.name.toLowerCase().includes(query) ||
				e.description.toLowerCase().includes(query),
		);
		const elapsed = performance.now() - start;

		expect(filtered.length).toBeGreaterThan(0);
		expect(elapsed).toBeLessThan(50);
	});

	it('sorts 5000 entities by name in under 50ms', () => {
		const entities = Array.from({ length: 5000 }, (_, i) => ({
			id: `entity-${i}`,
			name: `Entity ${5000 - i}`,
			entity_type: 'component',
		}));

		const start = performance.now();
		const sorted = [...entities].sort((a, b) => a.name.localeCompare(b.name));
		const elapsed = performance.now() - start;

		expect(sorted[0].name).toBe('Entity 1');
		expect(elapsed).toBeLessThan(50);
	});
});

describe('Type registry completeness', () => {
	it('Simple View has 7 entity types and 5 relationship types', () => {
		expect(SIMPLE_ENTITY_TYPES).toHaveLength(7);
		expect(SIMPLE_RELATIONSHIP_TYPES).toHaveLength(5);
	});

	it('UML has 6 entity types and 6 relationship types', () => {
		expect(UML_ENTITY_TYPES).toHaveLength(6);
		expect(UML_RELATIONSHIP_TYPES).toHaveLength(6);
	});

	it('ArchiMate has 11 entity types and 8 relationship types', () => {
		expect(ARCHIMATE_ENTITY_TYPES).toHaveLength(11);
		expect(ARCHIMATE_RELATIONSHIP_TYPES).toHaveLength(8);
	});

	it('total type count: 24 entity types + 19 relationship types', () => {
		const totalEntityTypes =
			SIMPLE_ENTITY_TYPES.length + UML_ENTITY_TYPES.length + ARCHIMATE_ENTITY_TYPES.length;
		const totalRelTypes =
			SIMPLE_RELATIONSHIP_TYPES.length +
			UML_RELATIONSHIP_TYPES.length +
			ARCHIMATE_RELATIONSHIP_TYPES.length;

		expect(totalEntityTypes).toBe(24);
		expect(totalRelTypes).toBe(19);
	});
});
