<script lang="ts">
	/**
	 * Main canvas component integrating Svelte Flow with Simple View
	 * node/edge types, zoom/pan, keyboard navigation, and ARIA announcer.
	 */
	import { SvelteFlow, Controls, Background } from '@xyflow/svelte';
	import { ConnectionMode } from '@xyflow/system';
	import '@xyflow/svelte/dist/style.css';

	import { simpleViewNodeTypes } from './nodes';
	import { simpleViewEdgeTypes } from './edges';
	import CanvasAnnouncer from './controls/CanvasAnnouncer.svelte';
	import KeyboardHandler from './controls/KeyboardHandler.svelte';
	import type { CanvasNode, CanvasEdge } from '$lib/types/canvas';

	interface Props {
		nodes: CanvasNode[];
		edges: CanvasEdge[];
		oncreatenode?: () => void;
		ondeletenode?: (nodeId: string) => void;
		onconnectnodes?: (sourceId: string, targetId: string) => void;
		ondeleteedge?: (edgeId: string) => void;
		onundo?: () => void;
		onredo?: () => void;
	}

	let {
		nodes = $bindable([]),
		edges = $bindable([]),
		oncreatenode,
		ondeletenode,
		onconnectnodes,
		ondeleteedge,
		onundo,
		onredo,
	}: Props = $props();

	let announcer: CanvasAnnouncer | undefined = $state();
	let keyboardHandler: KeyboardHandler | undefined = $state();

	let selectedNodeId = $state<string | null>(null);
	let selectedEdgeId = $state<string | null>(null);
	let connectMode = $state(false);
	let connectSourceId = $state<string | null>(null);

	function handleNodeClick({ node }: { node: CanvasNode; event: MouseEvent | TouchEvent }) {
		selectedNodeId = node.id;
		selectedEdgeId = null;
		announcer?.announce(`${node.data.label} selected, ${node.data.entityType}`);

		if (connectMode && connectSourceId && connectSourceId !== node.id) {
			handleConnect(connectSourceId, node.id);
		}
	}

	function handleEdgeClick({ edge }: { edge: CanvasEdge; event: MouseEvent }) {
		selectedEdgeId = edge.id;
		selectedNodeId = null;
		announcer?.announce(`Edge selected: ${edge.data?.label || edge.type || 'connection'}`);
	}

	function handleDeleteEdge(edgeId: string) {
		if (ondeleteedge) {
			ondeleteedge(edgeId);
		} else {
			edges = edges.filter((e) => e.id !== edgeId);
		}
		announcer?.announce('Edge deleted');
		selectedEdgeId = null;
	}

	function handleReconnect(oldEdge: CanvasEdge, newConnection: { source: string; target: string; sourceHandle?: string | null; targetHandle?: string | null }) {
		edges = edges.map((e) =>
			e.id === oldEdge.id
				? { ...e, source: newConnection.source, target: newConnection.target, sourceHandle: newConnection.sourceHandle ?? undefined, targetHandle: newConnection.targetHandle ?? undefined }
				: e,
		);
		announcer?.announce('Edge reconnected');
	}

	function handleSelect(nodeId: string | null) {
		selectedNodeId = nodeId;
		if (nodeId !== null) {
			selectedEdgeId = null;
		}
	}

	function handleMove(nodeId: string, dx: number, dy: number) {
		nodes = nodes.map((n) =>
			n.id === nodeId
				? { ...n, position: { x: n.position.x + dx, y: n.position.y + dy } }
				: n,
		);
	}

	function handleDelete(nodeId: string) {
		if (ondeletenode) {
			ondeletenode(nodeId);
		} else {
			nodes = nodes.filter((n) => n.id !== nodeId);
			edges = edges.filter((e) => e.source !== nodeId && e.target !== nodeId);
		}
		const deletedNode = nodes.find((n) => n.id === nodeId);
		announcer?.announce(`${deletedNode?.data.label ?? 'Node'} deleted`);
		selectedNodeId = null;
	}

	function handleConnect(sourceId: string, targetId: string) {
		if (onconnectnodes) {
			onconnectnodes(sourceId, targetId);
		} else {
			const newEdge: CanvasEdge = {
				id: `e-${sourceId}-${targetId}`,
				source: sourceId,
				target: targetId,
				type: 'uses',
				data: { relationshipType: 'uses' },
			};
			edges = [...edges, newEdge];
		}
		const sourceNode = nodes.find((n) => n.id === sourceId);
		const targetNode = nodes.find((n) => n.id === targetId);
		announcer?.announce(
			`Connected ${sourceNode?.data.label ?? 'source'} to ${targetNode?.data.label ?? 'target'}`,
		);
		connectMode = false;
		connectSourceId = null;
	}

	function handleToggleConnect() {
		if (connectMode) {
			connectMode = false;
			connectSourceId = null;
			announcer?.announce('Connect mode cancelled');
		} else if (selectedNodeId) {
			connectMode = true;
			connectSourceId = selectedNodeId;
			const node = nodes.find((n) => n.id === selectedNodeId);
			announcer?.announce(
				`Connect mode: select target for ${node?.data.label ?? 'node'}. Press Escape to cancel.`,
			);
		}
	}

	function handleCreate() {
		if (oncreatenode) {
			oncreatenode();
		}
	}

	function handleAnnounce(message: string) {
		announcer?.announce(message);
	}

	function handleKeydown(event: KeyboardEvent) {
		keyboardHandler?.handleKeydown(event);
	}
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div
	class="model-canvas"
	role="application"
	aria-label="Model diagram canvas{connectMode ? ' — connect mode active' : ''}"
	aria-roledescription="interactive diagram"
	onkeydown={handleKeydown}
>
	<SvelteFlow
		bind:nodes
		bind:edges
		nodeTypes={simpleViewNodeTypes}
		edgeTypes={simpleViewEdgeTypes}
		fitView
		connectionMode={ConnectionMode.Loose}
		onnodeclick={handleNodeClick}
		onedgeclick={handleEdgeClick}
		onreconnect={handleReconnect}
		proOptions={{ hideAttribution: true }}
		defaultEdgeOptions={{ type: 'uses' }}
	>
		<Controls showLock={false} />
		<Background />
		<KeyboardHandler
			bind:this={keyboardHandler}
			{nodes}
			{edges}
			{selectedNodeId}
			{selectedEdgeId}
			{connectMode}
			{connectSourceId}
			onselect={handleSelect}
			onmove={handleMove}
			ondelete={handleDelete}
			onconnect={handleConnect}
			oncreate={handleCreate}
			ontoggleconnect={handleToggleConnect}
			onannounce={handleAnnounce}
			ondeleteedge={handleDeleteEdge}
			{onundo}
			{onredo}
		/>
	</SvelteFlow>

	{#if connectMode}
		<div class="canvas-connect-indicator" aria-live="assertive">
			Connect mode — select target node or press Escape
		</div>
	{/if}

	<CanvasAnnouncer bind:this={announcer} />
</div>
