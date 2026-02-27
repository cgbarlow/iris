<script lang="ts">
	/**
	 * Read-only browse mode canvas. Displays models without editing capabilities.
	 * Used by viewers and reviewers per SPEC-005-A role-based access.
	 */
	import { SvelteFlow, Controls, Background } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';

	import { simpleViewNodeTypes } from './nodes';
	import { simpleViewEdgeTypes } from './edges';
	import CanvasAnnouncer from './controls/CanvasAnnouncer.svelte';
	import type { CanvasNode, CanvasEdge } from '$lib/types/canvas';

	interface Props {
		nodes: CanvasNode[];
		edges: CanvasEdge[];
		onnodeselect?: (nodeId: string) => void;
	}

	let { nodes, edges, onnodeselect }: Props = $props();

	let announcer: CanvasAnnouncer | undefined = $state();

	function handleNodeClick({ node }: { node: CanvasNode; event: MouseEvent | TouchEvent }) {
		announcer?.announce(`Viewing ${node.data.label}, ${node.data.entityType}`);
		onnodeselect?.(node.id);
	}
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div
	class="model-canvas model-canvas--browse"
	role="application"
	aria-label="Model diagram — browse mode (read-only)"
	aria-roledescription="interactive diagram, read-only"
>
	<SvelteFlow
		{nodes}
		{edges}
		nodeTypes={simpleViewNodeTypes}
		edgeTypes={simpleViewEdgeTypes}
		fitView
		nodesDraggable={false}
		nodesConnectable={false}
		elementsSelectable={true}
		onnodeclick={handleNodeClick}
		proOptions={{ hideAttribution: true }}
	>
		<Controls showLock={false} />
		<Background />
	</SvelteFlow>

	<div class="canvas-mode-badge" aria-live="polite">Browse Mode</div>

	<CanvasAnnouncer bind:this={announcer} />
</div>
