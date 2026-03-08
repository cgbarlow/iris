<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import type { CanvasNodeData } from '$lib/types/canvas';
	import { nodeOverrideStyle } from '$lib/canvas/utils/visualStyles';

	interface Props {
		data: CanvasNodeData;
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();

	const hasFixedSize = $derived(data.visual?.width != null && data.visual?.height != null);
	const visualStyle = $derived.by(() => {
		let style = nodeOverrideStyle(data.visual, hasFixedSize);
		if (data.visual?.bgColor) style += (style ? '; ' : '') + `--boundary-bg: ${data.visual.bgColor}`;
		if (data.visual?.borderColor) style += (style ? '; ' : '') + `--boundary-border: ${data.visual.borderColor}`;
		if (hasFixedSize) style += (style ? '; ' : '') + 'box-sizing: border-box';
		return style;
	});
</script>

<div
	class="canvas-node canvas-node--boundary"
	class:canvas-node--selected={selected}
	style={visualStyle}
	aria-label="{data.label}, Boundary"
>
	<div class="canvas-node__header">
		<span class="canvas-node__icon" aria-hidden="true">▧</span>
		<span class="canvas-node__label">{data.label}</span>
	</div>
	{#if data.description}
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
	<Handle type="source" position={Position.Top} id="top" style="top:0" />
	<Handle type="source" position={Position.Bottom} id="bottom" />
	<Handle type="target" position={Position.Bottom} id="bottom" style="bottom:0;top:auto" />
	<Handle type="target" position={Position.Left} id="left" />
	<Handle type="source" position={Position.Left} id="left" style="left:0" />
	<Handle type="source" position={Position.Right} id="right" />
	<Handle type="target" position={Position.Right} id="right" style="right:0;left:auto" />
	<Handle type="source" position={Position.Top} id="center" class="center-handle" style="left:50%;top:50%;transform:translate(-50%,-50%);" />
	<Handle type="target" position={Position.Top} id="center" class="center-handle" style="left:50%;top:50%;transform:translate(-50%,-50%);" />
</div>

<style>
	.canvas-node--boundary {
		background: var(--boundary-bg, transparent);
		border: 2px dashed var(--boundary-border, var(--color-muted, #6b7280));
		border-radius: 4px;
		padding: 8px;
		min-width: 160px;
		min-height: 80px;
		pointer-events: none;
	}
</style>
