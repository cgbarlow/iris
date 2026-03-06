<script lang="ts">
	import { getContext } from 'svelte';
	import { Handle, Position } from '@xyflow/svelte';
	import DOMPurify from 'dompurify';
	import type { CanvasNodeData, NotationType } from '$lib/types/canvas';
	import { nodeOverrideStyle } from '$lib/canvas/utils/visualStyles';
	import { getThemeRendering } from '$lib/stores/themeStore.svelte';

	interface Props {
		data: CanvasNodeData;
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();

	const notation = getContext<NotationType>('notation') ?? 'simple';
	const preferredThemeId = getContext<string | undefined>('preferredThemeId');
	const rendering = $derived(getThemeRendering(notation, preferredThemeId));
	const hideIcons = $derived(rendering?.hideIcons ?? false);
	const hasFixedSize = $derived(data.visual?.width != null && data.visual?.height != null);
	const visualStyle = $derived.by(() => {
		let style = nodeOverrideStyle(data.visual, hasFixedSize);
		if (data.visual?.bgColor) style += (style ? '; ' : '') + `--note-bg: ${data.visual.bgColor}`;
		if (data.visual?.borderColor) style += (style ? '; ' : '') + `--note-border: ${data.visual.borderColor}`;
		return style;
	});

	const sanitizedDescription = $derived(
		data.description ? DOMPurify.sanitize(data.description) : ''
	);
</script>

<div
	class="canvas-node canvas-node--note"
	class:canvas-node--selected={selected}
	style={visualStyle}
	aria-label="{data.label}, Note"
>
	<div class="canvas-node__header">
		{#if !hideIcons}
			<span class="canvas-node__icon" aria-hidden="true">📝</span>
		{/if}
		<span class="canvas-node__label">{data.label}</span>
	</div>
	{#if sanitizedDescription}
		<div class="canvas-node__description">{@html sanitizedDescription}</div>
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

<style>
	.canvas-node--note {
		background: var(--note-bg, #fef9c3);
		border: 1px solid var(--note-border, #ca8a04);
		border-radius: 2px;
		padding: 4px;
		min-width: 100px;
		position: relative;
		font-size: 8px;
		line-height: 1.2;
		overflow: hidden;
		word-break: break-word;
		overflow-wrap: break-word;
	}
	.canvas-node--note :global(.canvas-node__header) {
		font-weight: 700;
		font-size: 9px;
		flex-wrap: wrap;
	}
	.canvas-node--note :global(.canvas-node__header .canvas-node__label) {
		white-space: normal;
		text-overflow: unset;
		overflow: visible;
	}
	.canvas-node--note::before {
		content: '';
		position: absolute;
		top: 0;
		right: 0;
		width: 16px;
		height: 16px;
		background: linear-gradient(225deg, var(--note-bg, #fef9c3) 50%, var(--note-border, #ca8a04) 50%);
	}
	:global(.dark) .canvas-node--note {
		background: #422006;
		border-color: #a16207;
	}
	:global(.dark) .canvas-node--note::before {
		background: linear-gradient(225deg, #422006 50%, #a16207 50%);
	}
</style>
