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
	class="canvas-node canvas-node--actor"
	class:canvas-node--selected={selected}
	
	aria-label="{data.label}, Actor"
>
	<div class="canvas-node__header">
		<span class="canvas-node__icon" aria-hidden="true">👤</span>
		<span class="canvas-node__label">{data.label}</span>
	</div>
	{#if data.description}
		<div class="canvas-node__description">{data.description}</div>
	{/if}
	<Handle type="target" position={Position.Top} id="top" />
	<Handle type="source" position={Position.Bottom} id="bottom" />
	<Handle type="target" position={Position.Left} id="left" />
	<Handle type="source" position={Position.Right} id="right" />
</div>
