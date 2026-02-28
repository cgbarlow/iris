/** Canvas undo/redo history manager using Svelte 5 runes. */

import type { CanvasNode, CanvasEdge } from '$lib/types/canvas';

interface HistoryEntry {
	nodes: CanvasNode[];
	edges: CanvasEdge[];
}

const MAX_HISTORY = 50;

/** Deep clone that works with both plain objects and Svelte 5 $state proxies. */
function deepClone<T>(value: T): T {
	return JSON.parse(JSON.stringify(value));
}

export function createCanvasHistory() {
	let undoStack = $state<HistoryEntry[]>([]);
	let redoStack = $state<HistoryEntry[]>([]);

	function pushState(nodes: CanvasNode[], edges: CanvasEdge[]) {
		const entry: HistoryEntry = {
			nodes: deepClone(nodes),
			edges: deepClone(edges),
		};
		undoStack = [...undoStack.slice(-(MAX_HISTORY - 1)), entry];
		redoStack = []; // Clear redo on new action
	}

	function undo(currentNodes: CanvasNode[], currentEdges: CanvasEdge[]): HistoryEntry | null {
		if (undoStack.length === 0) return null;

		const current: HistoryEntry = {
			nodes: deepClone(currentNodes),
			edges: deepClone(currentEdges),
		};
		redoStack = [...redoStack, current];

		const previous = undoStack[undoStack.length - 1];
		undoStack = undoStack.slice(0, -1);
		return deepClone(previous);
	}

	function redo(currentNodes: CanvasNode[], currentEdges: CanvasEdge[]): HistoryEntry | null {
		if (redoStack.length === 0) return null;

		const current: HistoryEntry = {
			nodes: deepClone(currentNodes),
			edges: deepClone(currentEdges),
		};
		undoStack = [...undoStack, current];

		const next = redoStack[redoStack.length - 1];
		redoStack = redoStack.slice(0, -1);
		return deepClone(next);
	}

	function clear() {
		undoStack = [];
		redoStack = [];
	}

	return {
		pushState,
		undo,
		redo,
		clear,
		get canUndo() {
			return undoStack.length > 0;
		},
		get canRedo() {
			return redoStack.length > 0;
		},
	};
}
