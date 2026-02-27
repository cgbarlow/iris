<script lang="ts">
	/**
	 * Main canvas component integrating Svelte Flow with Simple View
	 * node/edge types, zoom/pan, and ARIA announcer.
	 */
	import { SvelteFlow, Controls, Background, useSvelteFlow } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';

	import { simpleViewNodeTypes } from './nodes';
	import { simpleViewEdgeTypes } from './edges';
	import CanvasAnnouncer from './controls/CanvasAnnouncer.svelte';
	import CanvasToolbar from './controls/CanvasToolbar.svelte';
	import type { CanvasNode, CanvasEdge } from '$lib/types/canvas';

	interface Props {
		nodes: CanvasNode[];
		edges: CanvasEdge[];
		onnodechange?: (changes: unknown[]) => void;
		onedgechange?: (changes: unknown[]) => void;
	}

	let { nodes = $bindable([]), edges = $bindable([]), onnodechange, onedgechange }: Props =
		$props();

	let announcer: CanvasAnnouncer | undefined = $state();

	const { fitView, zoomIn, zoomOut } = useSvelteFlow();

	function handleNodeClick({ node }: { node: CanvasNode; event: MouseEvent | TouchEvent }) {
		announcer?.announce(`${node.data.label} selected, ${node.data.entityType}`);
	}

	function handlePaneKeydown(event: KeyboardEvent) {
		if (event.ctrlKey || event.metaKey) {
			if (event.key === '=' || event.key === '+') {
				event.preventDefault();
				zoomIn();
				announcer?.announce('Zoomed in');
			} else if (event.key === '-') {
				event.preventDefault();
				zoomOut();
				announcer?.announce('Zoomed out');
			} else if (event.key === '0') {
				event.preventDefault();
				fitView();
				announcer?.announce('Fit to screen');
			}
		}
	}
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div
	class="model-canvas"
	role="application"
	aria-label="Model diagram canvas"
	aria-roledescription="interactive diagram"
	onkeydown={handlePaneKeydown}
>
	<SvelteFlow
		bind:nodes
		bind:edges
		nodeTypes={simpleViewNodeTypes}
		edgeTypes={simpleViewEdgeTypes}
		fitView
		onnodeclick={handleNodeClick}
		proOptions={{ hideAttribution: true }}
		defaultEdgeOptions={{ type: 'uses' }}
	>
		<Controls showLock={false} />
		<Background />
	</SvelteFlow>

	<CanvasToolbar
		onzoomin={() => {
			zoomIn();
			announcer?.announce('Zoomed in');
		}}
		onzoomout={() => {
			zoomOut();
			announcer?.announce('Zoomed out');
		}}
		onfit={() => {
			fitView();
			announcer?.announce('Fit to screen');
		}}
	/>

	<CanvasAnnouncer bind:this={announcer} />
</div>
