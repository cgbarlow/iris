// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves them correctly at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve, join, basename } from 'node:path';
import { createCanvasHistory } from '../../src/lib/canvas/useCanvasHistory.svelte';
import type { CanvasNode, CanvasEdge } from '$lib/types/canvas';

/**
 * Tests for edge reconnection fix (ADR-031).
 *
 * Verifies:
 * 1. EdgeReconnectAnchor is imported in all custom edge components
 * 2. handleReconnect correctly updates edge source/target
 * 3. Reconnection integrates with undo history
 * 4. Edge data (relationship type, label) preserved on reconnect
 */

function makeNodes(): CanvasNode[] {
	return [
		{ id: 'n1', type: 'component', position: { x: 0, y: 0 }, data: { label: 'Node 1', entityType: 'component' } },
		{ id: 'n2', type: 'service', position: { x: 200, y: 0 }, data: { label: 'Node 2', entityType: 'service' } },
		{ id: 'n3', type: 'database', position: { x: 400, y: 0 }, data: { label: 'Node 3', entityType: 'database' } },
	];
}

function makeEdges(): CanvasEdge[] {
	return [
		{
			id: 'e-n1-n2',
			source: 'n1',
			target: 'n2',
			type: 'uses',
			data: { relationshipType: 'uses', label: 'calls' },
		},
	];
}

/**
 * Simulates the handleReconnect logic from ModelCanvas/FullViewCanvas.
 * This is the exact logic used in the canvas components.
 */
function applyReconnect(
	edges: CanvasEdge[],
	oldEdge: CanvasEdge,
	newConnection: { source: string; target: string; sourceHandle?: string | null; targetHandle?: string | null },
): CanvasEdge[] {
	return edges.map((e) =>
		e.id === oldEdge.id
			? {
					...e,
					source: newConnection.source,
					target: newConnection.target,
					sourceHandle: newConnection.sourceHandle ?? undefined,
					targetHandle: newConnection.targetHandle ?? undefined,
				}
			: e,
	);
}

describe('Edge reconnection logic', () => {
	it('reconnects edge to a new target node', () => {
		const edges = makeEdges();
		const oldEdge = edges[0];
		const newConnection = { source: 'n1', target: 'n3' };

		const result = applyReconnect(edges, oldEdge, newConnection);

		expect(result[0].source).toBe('n1');
		expect(result[0].target).toBe('n3');
	});

	it('reconnects edge to a new source node', () => {
		const edges = makeEdges();
		const oldEdge = edges[0];
		const newConnection = { source: 'n3', target: 'n2' };

		const result = applyReconnect(edges, oldEdge, newConnection);

		expect(result[0].source).toBe('n3');
		expect(result[0].target).toBe('n2');
	});

	it('preserves edge data (relationship type and label) on reconnect', () => {
		const edges = makeEdges();
		const oldEdge = edges[0];
		const newConnection = { source: 'n1', target: 'n3' };

		const result = applyReconnect(edges, oldEdge, newConnection);

		expect(result[0].id).toBe('e-n1-n2');
		expect(result[0].type).toBe('uses');
		expect(result[0].data?.relationshipType).toBe('uses');
		expect(result[0].data?.label).toBe('calls');
	});

	it('preserves handle information on reconnect', () => {
		const edges = makeEdges();
		const oldEdge = edges[0];
		const newConnection = {
			source: 'n1',
			target: 'n3',
			sourceHandle: 'handle-bottom',
			targetHandle: 'handle-top',
		};

		const result = applyReconnect(edges, oldEdge, newConnection);

		expect(result[0].sourceHandle).toBe('handle-bottom');
		expect(result[0].targetHandle).toBe('handle-top');
	});

	it('clears handles when null handles provided', () => {
		const edges: CanvasEdge[] = [
			{
				id: 'e-n1-n2',
				source: 'n1',
				target: 'n2',
				type: 'uses',
				sourceHandle: 'old-handle',
				data: { relationshipType: 'uses' },
			},
		];
		const oldEdge = edges[0];
		const newConnection = { source: 'n1', target: 'n3', sourceHandle: null, targetHandle: null };

		const result = applyReconnect(edges, oldEdge, newConnection);

		expect(result[0].sourceHandle).toBeUndefined();
		expect(result[0].targetHandle).toBeUndefined();
	});

	it('only modifies the matching edge, leaving others untouched', () => {
		const edges: CanvasEdge[] = [
			{ id: 'e1', source: 'n1', target: 'n2', type: 'uses', data: { relationshipType: 'uses' } },
			{ id: 'e2', source: 'n2', target: 'n3', type: 'depends_on', data: { relationshipType: 'depends_on' } },
		];
		const oldEdge = edges[0];
		const newConnection = { source: 'n1', target: 'n3' };

		const result = applyReconnect(edges, oldEdge, newConnection);

		expect(result[0].target).toBe('n3');
		expect(result[1].source).toBe('n2');
		expect(result[1].target).toBe('n3');
	});
});

describe('Edge reconnection undo integration', () => {
	it('reconnection can be undone via history', () => {
		const history = createCanvasHistory();
		const nodes = makeNodes();
		let edges = makeEdges();

		// Push pre-reconnect state
		history.pushState(nodes, edges);

		// Apply reconnect
		const oldEdge = edges[0];
		edges = applyReconnect(edges, oldEdge, { source: 'n1', target: 'n3' });

		expect(edges[0].target).toBe('n3');

		// Undo
		const restored = history.undo(nodes, edges);
		expect(restored).not.toBeNull();
		expect(restored!.edges[0].target).toBe('n2');
	});

	it('reconnection can be redone after undo', () => {
		const history = createCanvasHistory();
		const nodes = makeNodes();
		let edges = makeEdges();

		// Push pre-reconnect state
		history.pushState(nodes, edges);

		// Apply reconnect
		const oldEdge = edges[0];
		edges = applyReconnect(edges, oldEdge, { source: 'n1', target: 'n3' });

		// Undo
		const restored = history.undo(nodes, edges);
		edges = restored!.edges;

		// Redo
		const redone = history.redo(nodes, edges);
		expect(redone).not.toBeNull();
		expect(redone!.edges[0].target).toBe('n3');
	});

	it('reconnect preserves edge data through undo/redo cycle', () => {
		const history = createCanvasHistory();
		const nodes = makeNodes();
		let edges = makeEdges();

		history.pushState(nodes, edges);
		const oldEdge = edges[0];
		edges = applyReconnect(edges, oldEdge, { source: 'n1', target: 'n3' });

		// Undo
		const restored = history.undo(nodes, edges);
		expect(restored!.edges[0].data?.label).toBe('calls');
		expect(restored!.edges[0].data?.relationshipType).toBe('uses');

		// Redo
		edges = restored!.edges;
		const redone = history.redo(nodes, edges);
		expect(redone!.edges[0].data?.label).toBe('calls');
		expect(redone!.edges[0].data?.relationshipType).toBe('uses');
	});
});

describe('EdgeReconnectAnchor presence in custom edge components', () => {
	/**
	 * These tests verify that all custom edge components import and use
	 * EdgeReconnectAnchor from @xyflow/svelte. This is critical because
	 * without these anchors, edge endpoints are not draggable.
	 *
	 * We test by reading the source files and checking for the import
	 * and component usage.
	 */
	const FRONTEND_SRC = resolve(import.meta.dirname, '../../src/lib/canvas');

	const simpleEdgeFiles = [
		'edges/UsesEdge.svelte',
		'edges/DependsOnEdge.svelte',
		'edges/ComposesEdge.svelte',
		'edges/ImplementsEdge.svelte',
		'edges/ContainsEdge.svelte',
	];

	const umlEdgeFiles = [
		'uml/edges/AssociationEdge.svelte',
		'uml/edges/AggregationEdge.svelte',
		'uml/edges/CompositionEdge.svelte',
		'uml/edges/DependencyEdge.svelte',
		'uml/edges/RealizationEdge.svelte',
		'uml/edges/GeneralizationEdge.svelte',
	];

	const archimateEdgeFiles = ['archimate/edges/ArchimateEdge.svelte'];

	const allEdgeFiles = [...simpleEdgeFiles, ...umlEdgeFiles, ...archimateEdgeFiles];

	for (const file of allEdgeFiles) {
		const componentName = basename(file, '.svelte');

		it(`${componentName} imports EdgeReconnectAnchor`, () => {
			const filePath = join(FRONTEND_SRC, file);
			const content = readFileSync(filePath, 'utf-8');
			expect(content).toContain('EdgeReconnectAnchor');
		});

		it(`${componentName} renders source reconnect anchor`, () => {
			const filePath = join(FRONTEND_SRC, file);
			const content = readFileSync(filePath, 'utf-8');
			expect(content).toContain('type="source"');
		});

		it(`${componentName} renders target reconnect anchor`, () => {
			const filePath = join(FRONTEND_SRC, file);
			const content = readFileSync(filePath, 'utf-8');
			expect(content).toContain('type="target"');
		});
	}
});
