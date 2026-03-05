<script lang="ts">
	/**
	 * BaseNode: Shared node logic for all canvas node types.
	 * Provides connection handles, selection state, browseMode navigation,
	 * label/description display, and accessibility labels.
	 *
	 * Used as fallback by DynamicNode and as a wrapper by notation renderers.
	 */
	import { Handle, Position } from '@xyflow/svelte';
	import type { Snippet } from 'svelte';
	import type { CanvasNodeData } from '$lib/types/canvas';
	import { nodeOverrideStyle } from '$lib/canvas/utils/visualStyles';

	interface Props {
		data: CanvasNodeData;
		selected?: boolean;
		icon?: string;
		typeLabel?: string;
		cssClass?: string;
		children?: Snippet;
	}

	let {
		data,
		selected = false,
		icon = '⬡',
		typeLabel = 'element',
		cssClass = '',
		children,
	}: Props = $props();

	const visualStyle = $derived(nodeOverrideStyle(data.visual));
</script>

<div
	class="canvas-node {cssClass}"
	class:canvas-node--selected={selected}
	style={visualStyle}
	aria-label="{data.label}, {typeLabel}"
>
	<div class="canvas-node__header">
		<span class="canvas-node__icon" aria-hidden="true">{icon}</span>
		<span class="canvas-node__label">{data.label}</span>
	</div>
	{#if children}
		{@render children()}
	{/if}
	{#if data.description && !children}
		<div class="canvas-node__description">{data.description}</div>
	{/if}
	{#if data.browseMode && data.entityId}
		<a
			href="/elements/{data.entityId}"
			class="canvas-node__browse-link"
			aria-label="View {data.label} details"
		>
			View details
		</a>
	{/if}
	<Handle type="target" position={Position.Top} id="top" />
	<Handle type="source" position={Position.Bottom} id="bottom" />
	<Handle type="target" position={Position.Left} id="left" />
	<Handle type="source" position={Position.Right} id="right" />
	<Handle type="source" position={Position.Top} id="center" class="center-handle" style="left:50%;top:50%;transform:translate(-50%,-50%);" />
	<Handle type="target" position={Position.Top} id="center" class="center-handle" style="left:50%;top:50%;transform:translate(-50%,-50%);" />
</div>
