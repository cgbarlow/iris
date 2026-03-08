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

	/** Strip HTML tags to get plain text for comparison */
	function stripHtml(html: string): string {
		return html.replace(/<[^>]*>/g, '').replace(/\r\n/g, '\n').trim();
	}

	const descriptionPlain = $derived(stripHtml(sanitizedDescription));
	const labelTrimmed = $derived((data.label ?? '').trim());

	/**
	 * Deduplication logic:
	 * - If plain description equals label → show header only (skip description)
	 * - If plain description starts with label → show description only (skip header, it's redundant)
	 * - Otherwise → show both
	 */
	const showHeader = $derived(
		!(sanitizedDescription && descriptionPlain.startsWith(labelTrimmed) && descriptionPlain !== labelTrimmed)
	);
	const showDescription = $derived(
		!!(sanitizedDescription && descriptionPlain !== labelTrimmed)
	);
</script>

<div
	class="canvas-node canvas-node--note"
	class:canvas-node--selected={selected}
	style={visualStyle}
	aria-label="{data.label}, Note"
>
	{#if showHeader}
		<div class="canvas-node__header">
			{#if !hideIcons}
				<span class="canvas-node__icon" aria-hidden="true">📝</span>
			{/if}
			<span class="canvas-node__label">{data.label}</span>
		</div>
	{/if}
	{#if showDescription}
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
		box-sizing: border-box;
	}
	.canvas-node--note :global(.canvas-node__header) {
		font-weight: normal;
		font-size: 9px;
		flex-wrap: wrap;
	}
	.canvas-node--note :global(.canvas-node__header .canvas-node__label) {
		white-space: normal;
		text-overflow: unset;
		overflow: visible;
	}
	.canvas-node--note :global(.canvas-node__description ol),
	.canvas-node--note :global(.canvas-node__description ul) {
		margin: 2px 0;
		padding-left: 16px;
	}
	.canvas-node--note :global(.canvas-node__description ol) {
		list-style: decimal;
	}
	.canvas-node--note :global(.canvas-node__description ul) {
		list-style: disc;
	}
	.canvas-node--note :global(.canvas-node__description li) {
		margin: 1px 0;
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
