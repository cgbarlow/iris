<script lang="ts">
	/**
	 * UnifiedCanvas: Single canvas component replacing ModelCanvas, FullViewCanvas,
	 * and BrowseCanvas. Sets notation context for DynamicNode/DynamicEdge dispatch.
	 * Supports both edit and browse modes.
	 */
	import { setContext } from 'svelte';
	import { SvelteFlow, Controls, Background } from '@xyflow/svelte';
	import { ConnectionMode } from '@xyflow/system';
	import '@xyflow/svelte/dist/style.css';

	import { unifiedNodeTypes, unifiedEdgeTypes } from './registry';
	import CanvasAnnouncer from './controls/CanvasAnnouncer.svelte';
	import KeyboardHandler from './controls/KeyboardHandler.svelte';
	import type { CanvasNode, CanvasEdge, NotationType } from '$lib/types/canvas';

	interface Props {
		notation: NotationType;
		nodes: CanvasNode[];
		edges: CanvasEdge[];
		browseMode?: boolean;
		oncreatenode?: () => void;
		ondeletenode?: (nodeId: string) => void;
		onconnectnodes?: (sourceId: string, targetId: string) => void;
		ondeleteedge?: (edgeId: string) => void;
		onreconnectedge?: () => void;
		onedgeselect?: (edgeId: string | null) => void;
		onnodeselect?: (nodeId: string | null) => void;
		onundo?: () => void;
		onredo?: () => void;
		onnodedragstart?: () => void;
	}

	let {
		notation,
		nodes = $bindable([]),
		edges = $bindable([]),
		browseMode = false,
		oncreatenode,
		ondeletenode,
		onconnectnodes,
		ondeleteedge,
		onreconnectedge,
		onedgeselect,
		onnodeselect,
		onundo,
		onredo,
		onnodedragstart,
	}: Props = $props();

	// Set notation context for DynamicNode/DynamicEdge to read
	setContext('notation', notation);

	let announcer: CanvasAnnouncer | undefined = $state();
	let keyboardHandler: KeyboardHandler | undefined = $state();

	let selectedNodeId = $state<string | null>(null);
	let selectedEdgeId = $state<string | null>(null);
	let connectMode = $state(false);
	let connectSourceId = $state<string | null>(null);

	/** Map nodes to include browseMode flag when in browse mode. */
	const displayNodes = $derived(
		browseMode
			? nodes.map((n) => ({ ...n, data: { ...n.data, browseMode: true } }))
			: nodes
	);

	/** Default edge type based on notation. */
	const defaultEdgeType = $derived(
		notation === 'uml' ? 'association' :
		notation === 'archimate' ? 'serving' :
		'uses'
	);

	const notationLabel = $derived(
		notation === 'uml' ? 'UML' :
		notation === 'archimate' ? 'ArchiMate' :
		notation === 'c4' ? 'C4' :
		'Simple'
	);

	function handleNodeClick({ node }: { node: CanvasNode; event: MouseEvent | TouchEvent }) {
		selectedNodeId = node.id;
		selectedEdgeId = null;
		onedgeselect?.(null);
		onnodeselect?.(node.id);
		announcer?.announce(`${node.data.label} selected, ${node.data.entityType}`);

		if (!browseMode && connectMode && connectSourceId && connectSourceId !== node.id) {
			handleConnect(connectSourceId, node.id);
		}
	}

	function handleEdgeClick({ edge }: { edge: CanvasEdge; event: MouseEvent }) {
		if (browseMode) return;
		selectedEdgeId = edge.id;
		selectedNodeId = null;
		onedgeselect?.(edge.id);
		onnodeselect?.(null);
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
		onedgeselect?.(null);
	}

	function handleReconnect(oldEdge: CanvasEdge, newConnection: { source: string; target: string; sourceHandle?: string | null; targetHandle?: string | null }) {
		onreconnectedge?.();
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
			const isSelfLoop = sourceId === targetId;
			const newEdge: CanvasEdge = {
				id: `e-${sourceId}-${targetId}`,
				source: sourceId,
				target: targetId,
				type: isSelfLoop ? 'self_loop' : defaultEdgeType,
				...(isSelfLoop ? { sourceHandle: 'right', targetHandle: 'top' } : {}),
				data: { relationshipType: defaultEdgeType as any },
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
	class="model-canvas{browseMode ? ' model-canvas--browse' : ''}"
	role="application"
	aria-label="{notationLabel} diagram canvas{browseMode ? ' — browse mode (read-only)' : ''}{connectMode ? ' — connect mode active' : ''}"
	aria-roledescription="interactive diagram{browseMode ? ', read-only' : ''}"
	onkeydown={browseMode ? undefined : handleKeydown}
>
	{#if browseMode}
		<SvelteFlow
			nodes={displayNodes}
			edges={edges}
			nodeTypes={unifiedNodeTypes}
			edgeTypes={unifiedEdgeTypes}
			fitView
			onnodeclick={handleNodeClick}
			proOptions={{ hideAttribution: true }}
			nodesDraggable={false}
			nodesConnectable={false}
			elementsSelectable={true}
		>
			<Controls showLock={false} />
			<Background />
		</SvelteFlow>
	{:else}
		<SvelteFlow
			bind:nodes
			bind:edges
			nodeTypes={unifiedNodeTypes}
			edgeTypes={unifiedEdgeTypes}
			fitView
			connectionMode={ConnectionMode.Loose}
			onnodeclick={handleNodeClick}
			onedgeclick={handleEdgeClick}
			onreconnect={handleReconnect}
			onnodedragstart={() => onnodedragstart?.()}
			proOptions={{ hideAttribution: true }}
			defaultEdgeOptions={{ type: defaultEdgeType }}
			nodesDraggable={true}
			nodesConnectable={!connectMode}
			elementsSelectable={true}
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
	{/if}

	{#if connectMode}
		<div class="canvas-connect-indicator" aria-live="assertive">
			Connect mode — select target node or press Escape
		</div>
	{/if}

	{#if browseMode}
		<div class="canvas-mode-badge" aria-live="polite">Browse Mode</div>
	{/if}

	<CanvasAnnouncer bind:this={announcer} />
</div>
