<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import type { CanvasNodeData } from '$lib/types/canvas';

	interface Props {
		data: CanvasNodeData;
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();
</script>

<div
	class="canvas-node canvas-node--modelref"
	class:canvas-node--selected={selected}
	aria-label="{data.label}, Model Reference"
>
	<!-- Stacked squares visual: two offset background layers -->
	<div class="canvas-node--modelref__stack" aria-hidden="true"></div>
	<div class="canvas-node__header">
		<span class="canvas-node__icon" aria-hidden="true">▣</span>
		<span class="canvas-node__label">{data.label}</span>
	</div>
	{#if data.description}
		<div class="canvas-node__description">{data.description}</div>
	{/if}
	{#if data.browseMode && data.linkedModelId}
		<a
			href="/models/{data.linkedModelId}"
			class="canvas-node__browse-link"
			aria-label="View {data.label} model"
		>
			View model
		</a>
	{:else if data.browseMode && data.entityId}
		<a
			href="/entities/{data.entityId}"
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
</div>
