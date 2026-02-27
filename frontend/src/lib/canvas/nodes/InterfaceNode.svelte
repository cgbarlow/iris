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
	class="canvas-node canvas-node--interface"
	class:canvas-node--selected={selected}
	
	aria-label="{data.label}, Interface"
>
	<div class="canvas-node__header">
		<span class="canvas-node__icon" aria-hidden="true">◯</span>
		<span class="canvas-node__label">{data.label}</span>
	</div>
	{#if data.description}
		<div class="canvas-node__description">{data.description}</div>
	{/if}
	<Handle type="target" position={Position.Top} />
	<Handle type="source" position={Position.Bottom} />
</div>
