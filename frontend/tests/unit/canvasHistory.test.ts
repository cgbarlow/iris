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
});
