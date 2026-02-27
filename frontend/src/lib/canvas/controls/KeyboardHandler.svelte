<script lang="ts">
	/**
	 * Canvas keyboard navigation handler.
	 * Provides full keyboard equivalents for all canvas operations per WCAG 2.1.3.
	 */
	import { useSvelteFlow } from '@xyflow/svelte';
	import type { CanvasNode, CanvasEdge } from '$lib/types/canvas';

	interface Props {
		nodes: CanvasNode[];
		edges: CanvasEdge[];
		selectedNodeId: string | null;
		connectMode: boolean;
		connectSourceId: string | null;
		onselect: (nodeId: string | null) => void;
		onmove: (nodeId: string, dx: number, dy: number) => void;
		ondelete: (nodeId: string) => void;
		onconnect: (sourceId: string, targetId: string) => void;
		oncreate: () => void;
		ontoggleconnect: () => void;
		onannounce: (message: string) => void;
	}

	let {
		nodes,
		edges,
		selectedNodeId,
		connectMode,
		connectSourceId,
		onselect,
		onmove,
		ondelete,
		onconnect,
		oncreate,
		ontoggleconnect,
		onannounce,
	}: Props = $props();

	const { fitView, zoomIn, zoomOut } = useSvelteFlow();

	const MOVE_STEP = 10;
	const MOVE_STEP_LARGE = 50;

	function getNodeIndex(nodeId: string | null): number {
		if (!nodeId) return -1;
		return nodes.findIndex((n) => n.id === nodeId);
	}

	function selectByIndex(index: number) {
		if (index >= 0 && index < nodes.length) {
			const node = nodes[index];
			onselect(node.id);
			onannounce(
				`${node.data.label}, ${node.data.entityType}, position ${Math.round(node.position.x)}, ${Math.round(node.position.y)}`,
			);
		}
	}

	export function handleKeydown(event: KeyboardEvent) {
		const ctrl = event.ctrlKey || event.metaKey;

		// Zoom shortcuts
		if (ctrl) {
			if (event.key === '=' || event.key === '+') {
				event.preventDefault();
				zoomIn();
				onannounce('Zoomed in');
				return;
			}
			if (event.key === '-') {
				event.preventDefault();
				zoomOut();
				onannounce('Zoomed out');
				return;
			}
			if (event.key === '0') {
				event.preventDefault();
				fitView();
				onannounce('Fit to screen');
				return;
			}
			if (event.key === 'n' || event.key === 'N') {
				event.preventDefault();
				oncreate();
				return;
			}
		}

		// Connect mode toggle
		if (event.key === 'c' || event.key === 'C') {
			if (!ctrl && selectedNodeId) {
				event.preventDefault();
				ontoggleconnect();
				return;
			}
		}

		// No nodes? Nothing else to do
		if (nodes.length === 0) return;

		const currentIndex = getNodeIndex(selectedNodeId);

		// Tab / arrow navigation through nodes
		if (event.key === 'Tab' && !ctrl) {
			event.preventDefault();
			if (event.shiftKey) {
				const prev = currentIndex <= 0 ? nodes.length - 1 : currentIndex - 1;
				selectByIndex(prev);
			} else {
				const next = currentIndex >= nodes.length - 1 ? 0 : currentIndex + 1;
				selectByIndex(next);
			}
			return;
		}

		// Arrow keys: move selected node or navigate
		if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
			event.preventDefault();

			if (selectedNodeId) {
				const step = event.shiftKey ? MOVE_STEP_LARGE : MOVE_STEP;
				let dx = 0;
				let dy = 0;

				switch (event.key) {
					case 'ArrowUp':
						dy = -step;
						break;
					case 'ArrowDown':
						dy = step;
						break;
					case 'ArrowLeft':
						dx = -step;
						break;
					case 'ArrowRight':
						dx = step;
						break;
				}

				onmove(selectedNodeId, dx, dy);
				const node = nodes.find((n) => n.id === selectedNodeId);
				if (node) {
					onannounce(
						`Moved to ${Math.round(node.position.x + dx)}, ${Math.round(node.position.y + dy)}`,
					);
				}
			}
			return;
		}

		// Enter/Space: select or confirm connect
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();

			if (connectMode && connectSourceId && selectedNodeId && connectSourceId !== selectedNodeId) {
				onconnect(connectSourceId, selectedNodeId);
				return;
			}

			if (selectedNodeId) {
				const node = nodes.find((n) => n.id === selectedNodeId);
				if (node) {
					onannounce(`${node.data.label} selected`);
				}
			}
			return;
		}

		// Delete key
		if (event.key === 'Delete' || event.key === 'Backspace') {
			if (selectedNodeId && !ctrl) {
				event.preventDefault();
				ondelete(selectedNodeId);
			}
			return;
		}

		// Escape: deselect or exit connect mode
		if (event.key === 'Escape') {
			if (connectMode) {
				ontoggleconnect();
			} else {
				onselect(null);
				onannounce('Selection cleared');
			}
			return;
		}

		// F key: fit/focus selected node
		if (event.key === 'f' || event.key === 'F') {
			if (!ctrl && selectedNodeId) {
				event.preventDefault();
				const node = nodes.find((n) => n.id === selectedNodeId);
				if (node) {
					fitView({ nodes: [node], duration: 300 });
					onannounce(`Focused on ${node.data.label}`);
				}
			}
		}
	}
</script>
