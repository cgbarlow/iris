import { describe, it, expect } from 'vitest';
import { createCanvasHistory } from '../../src/lib/canvas/useCanvasHistory.svelte';

describe('createCanvasHistory', () => {
	function makeNodes(count: number) {
		return Array.from({ length: count }, (_, i) => ({
			id: `n${i}`,
			type: 'component' as const,
			position: { x: i * 100, y: 0 },
			data: { label: `Node ${i}`, entityType: 'component' as const },
		}));
	}

	function makeEdges(count: number) {
		return Array.from({ length: count }, (_, i) => ({
			id: `e${i}`,
			source: `n${i}`,
			target: `n${i + 1}`,
			data: { relationshipType: 'uses' as const },
		}));
	}

	it('starts with empty stacks', () => {
		const history = createCanvasHistory();
		expect(history.canUndo).toBe(false);
		expect(history.canRedo).toBe(false);
	});

	it('pushState enables undo', () => {
		const history = createCanvasHistory();
		history.pushState(makeNodes(1), []);
		expect(history.canUndo).toBe(true);
	});

	it('undo restores previous state', () => {
		const history = createCanvasHistory();
		const nodes1 = makeNodes(1);
		history.pushState(nodes1, []);

		const nodes2 = makeNodes(2);
		const result = history.undo(nodes2, []);
		expect(result).not.toBeNull();
		expect(result!.nodes).toHaveLength(1);
	});

	it('redo restores undone state', () => {
		const history = createCanvasHistory();
		const nodes1 = makeNodes(1);
		history.pushState(nodes1, []);

		const nodes2 = makeNodes(2);
		history.undo(nodes2, []);

		const result = history.redo(nodes1, []);
		expect(result).not.toBeNull();
		expect(result!.nodes).toHaveLength(2);
	});

	it('new action after undo clears redo stack', () => {
		const history = createCanvasHistory();
		history.pushState(makeNodes(1), []);
		history.undo(makeNodes(2), []);
		expect(history.canRedo).toBe(true);

		history.pushState(makeNodes(3), []);
		expect(history.canRedo).toBe(false);
	});

	it('returns null when nothing to undo', () => {
		const history = createCanvasHistory();
		const result = history.undo(makeNodes(1), []);
		expect(result).toBeNull();
	});

	it('returns null when nothing to redo', () => {
		const history = createCanvasHistory();
		const result = history.redo(makeNodes(1), []);
		expect(result).toBeNull();
	});

	it('pushState on node drag start enables undo to restore pre-drag positions', () => {
		const history = createCanvasHistory();

		// Node starts at position (0, 0)
		const preDragNodes = [
			{
				id: 'n0',
				type: 'component' as const,
				position: { x: 0, y: 0 },
				data: { label: 'Node 0', entityType: 'component' as const },
			},
		];

		// Simulate drag start: push pre-drag state
		history.pushState(preDragNodes, []);
		expect(history.canUndo).toBe(true);

		// After drag, node is at new position (100, 50)
		const postDragNodes = [
			{
				id: 'n0',
				type: 'component' as const,
				position: { x: 100, y: 50 },
				data: { label: 'Node 0', entityType: 'component' as const },
			},
		];

		// Undo should restore the pre-drag position
		const result = history.undo(postDragNodes, []);
		expect(result).not.toBeNull();
		expect(result!.nodes).toHaveLength(1);
		expect(result!.nodes[0].position).toEqual({ x: 0, y: 0 });
	});

	it('undo after node drag restores original node positions', () => {
		const history = createCanvasHistory();

		// Initial state: two nodes at known positions
		const initialNodes = [
			{
				id: 'n0',
				type: 'component' as const,
				position: { x: 10, y: 20 },
				data: { label: 'A', entityType: 'component' as const },
			},
			{
				id: 'n1',
				type: 'component' as const,
				position: { x: 200, y: 300 },
				data: { label: 'B', entityType: 'component' as const },
			},
		];
		const initialEdges = [
			{
				id: 'e0',
				source: 'n0',
				target: 'n1',
				data: { relationshipType: 'uses' as const },
			},
		];

		// Push pre-drag state (simulating onnodedragstart)
		history.pushState(initialNodes, initialEdges);

		// After drag, node n0 has moved
		const movedNodes = [
			{
				id: 'n0',
				type: 'component' as const,
				position: { x: 500, y: 600 },
				data: { label: 'A', entityType: 'component' as const },
			},
			{
				id: 'n1',
				type: 'component' as const,
				position: { x: 200, y: 300 },
				data: { label: 'B', entityType: 'component' as const },
			},
		];

		// Undo restores original positions
		const result = history.undo(movedNodes, initialEdges);
		expect(result).not.toBeNull();
		expect(result!.nodes[0].position).toEqual({ x: 10, y: 20 });
		expect(result!.nodes[1].position).toEqual({ x: 200, y: 300 });
		expect(result!.edges).toHaveLength(1);

		// Redo restores the moved positions
		const redoResult = history.redo(result!.nodes, result!.edges);
		expect(redoResult).not.toBeNull();
		expect(redoResult!.nodes[0].position).toEqual({ x: 500, y: 600 });
	});
});
