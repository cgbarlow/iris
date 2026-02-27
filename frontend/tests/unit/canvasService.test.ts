import { describe, it, expect } from 'vitest';
import {
	createCanvasNode,
	createCanvasEdge,
	nodesToPlacements,
	buildModelVersionData,
	generateNodeId,
	generateEdgeId,
} from '$lib/canvas/canvasService';

describe('canvasService', () => {
	it('creates canvas node with sanitized label', () => {
		const node = createCanvasNode(
			'n1',
			'<script>alert("xss")</script>My Service',
			'service',
			{ x: 100, y: 200 },
			'entity-123',
		);
		expect(node.id).toBe('n1');
		expect(node.type).toBe('service');
		expect(node.position).toEqual({ x: 100, y: 200 });
		expect(node.data.label).not.toContain('<script>');
		expect(node.data.label).toContain('My Service');
		expect(node.data.entityType).toBe('service');
		expect(node.data.entityId).toBe('entity-123');
	});

	it('creates canvas edge with relationship metadata', () => {
		const edge = createCanvasEdge('e1', 'n1', 'n2', 'uses', 'rel-456', 'calls');
		expect(edge.id).toBe('e1');
		expect(edge.source).toBe('n1');
		expect(edge.target).toBe('n2');
		expect(edge.type).toBe('uses');
		expect(edge.data?.relationshipType).toBe('uses');
		expect(edge.data?.relationshipId).toBe('rel-456');
		expect(edge.data?.label).toBe('calls');
	});

	it('converts nodes to placements', () => {
		const nodes = [
			createCanvasNode('n1', 'A', 'component', { x: 10, y: 20 }, 'e1'),
			createCanvasNode('n2', 'B', 'database', { x: 50, y: 60 }, 'e2'),
		];
		const placements = nodesToPlacements(nodes);
		expect(placements).toHaveLength(2);
		expect(placements[0].entity_id).toBe('e1');
		expect(placements[0].position).toEqual({ x: 10, y: 20 });
		expect(placements[1].entity_id).toBe('e2');
	});

	it('builds model version data from canvas state', () => {
		const nodes = [createCanvasNode('n1', 'Svc', 'service', { x: 0, y: 0 }, 'e1')];
		const edges = [createCanvasEdge('e1', 'n1', 'n2', 'uses', 'rel-1')];
		const data = buildModelVersionData(nodes, edges);
		expect(data.placements).toHaveLength(1);
		expect(data.displayed_relationships).toEqual(['rel-1']);
		expect(data.canvas.viewport.zoom).toBe(1.0);
		expect(data.canvas.grid.enabled).toBe(true);
	});

	it('generates unique node IDs', () => {
		const id1 = generateNodeId();
		const id2 = generateNodeId();
		expect(id1).not.toBe(id2);
	});

	it('generates unique edge IDs', () => {
		const id1 = generateEdgeId();
		const id2 = generateEdgeId();
		expect(id1).not.toBe(id2);
	});

	it('handles node without entityId in placements', () => {
		const nodes = [createCanvasNode('n1', 'Test', 'actor', { x: 30, y: 40 })];
		const placements = nodesToPlacements(nodes);
		expect(placements[0].entity_id).toBe('n1');
	});

	it('filters edges without relationshipId in model version data', () => {
		const nodes = [createCanvasNode('n1', 'A', 'queue', { x: 0, y: 0 })];
		const edges = [createCanvasEdge('e1', 'n1', 'n2', 'depends_on')];
		const data = buildModelVersionData(nodes, edges);
		expect(data.displayed_relationships).toEqual([]);
	});
});
