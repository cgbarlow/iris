<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import DOMPurify from 'dompurify';
	import type { CanvasNodeData } from '$lib/types/canvas';

	interface Props {
		data: CanvasNodeData;
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();

	const sanitizedDescription = $derived(
		data.description ? DOMPurify.sanitize(data.description) : ''
	);
</script>

<div
	class="canvas-node canvas-node--note"
	class:canvas-node--selected={selected}
	aria-label="{data.label}, Note"
>
	<div class="canvas-node__header">
		<span class="canvas-node__icon" aria-hidden="true">📝</span>
		<span class="canvas-node__label">{data.label}</span>
	</div>
	{#if sanitizedDescription}
		<div class="canvas-node__description">{@html sanitizedDescription}</div>
	{/if}
	{#if data.browseMode && data.entityId}
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
	<Handle type="source" position={Position.Top} id="center" class="center-handle" style="left:50%;top:50%;transform:translate(-50%,-50%);" />
	<Handle type="target" position={Position.Top} id="center" class="center-handle" style="left:50%;top:50%;transform:translate(-50%,-50%);" />
</div>

<style>
	.canvas-node--note {
		background: #fef9c3;
		border: 1px solid #ca8a04;
		border-radius: 2px;
		padding: 8px;
		min-width: 120px;
		position: relative;
	}
	.canvas-node--note::before {
		content: '';
		position: absolute;
		top: 0;
		right: 0;
		width: 16px;
		height: 16px;
		background: linear-gradient(225deg, #fef9c3 50%, #ca8a04 50%);
	}
	:global(.dark) .canvas-node--note {
		background: #422006;
		border-color: #a16207;
	}
	:global(.dark) .canvas-node--note::before {
		background: linear-gradient(225deg, #422006 50%, #a16207 50%);
	}
</style>
