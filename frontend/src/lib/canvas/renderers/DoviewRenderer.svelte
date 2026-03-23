<script lang="ts">
	/**
	 * DoviewRenderer: Renders nodes in DoView notation (ADR-094).
	 * Supports outcome_box, final_outcome, overview_tile, and source_reference types.
	 * Colors are theme-driven via the doview-default theme (10-color palette).
	 * Text wrapping and alignment are controlled by the theme rendering config.
	 */
	import { getContext } from 'svelte';
	import BaseNode from '../BaseNode.svelte';
	import type { CanvasNodeData, NotationType } from '$lib/types/canvas';
	import { getThemeRendering } from '$lib/stores/themeStore.svelte';

	interface Props {
		data: CanvasNodeData;
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();

	const notation = getContext<NotationType>('notation') ?? 'doview';
	const rendering = $derived(getThemeRendering(notation));
	const wrapLabels = $derived(rendering?.wrapLabels ?? false);
	const textAlign = $derived(rendering?.textAlign ?? 'left');

	const DOVIEW_ICONS: Record<string, string> = {
		outcome_box:      '▭',
		final_outcome:    '★',
		overview_tile:    '⬡',
		source_reference: '◧',
	};

	const icon = $derived(DOVIEW_ICONS[data.entityType] ?? '▭');
	const isFinalOutcome = $derived(data.entityType === 'final_outcome');
</script>

<div
	class="doview-node doview-node--{data.entityType}"
	class:doview-node--final={isFinalOutcome}
	class:doview-node--wrap={wrapLabels}
	style="--doview-text-align: {textAlign};"
>
	<BaseNode
		{data}
		{selected}
		{icon}
		typeLabel={data.entityType.replace(/_/g, ' ')}
		cssClass="canvas-node--{data.entityType}"
	/>
</div>

<style>
	.doview-node {
		width: 100%;
		height: 100%;
	}

	/* Theme-driven: wrap labels when wrapLabels is true */
	.doview-node--wrap :global(.canvas-node__label) {
		white-space: normal;
		word-wrap: break-word;
		overflow-wrap: break-word;
		overflow: visible;
		text-overflow: unset;
		line-height: 1.3;
	}

	/* Theme-driven: text alignment and vertical centering */
	.doview-node :global(.canvas-node) {
		display: flex;
		flex-direction: column;
		justify-content: center;
		text-align: var(--doview-text-align, center);
	}

	.doview-node :global(.canvas-node__header) {
		justify-content: var(--doview-text-align, center);
	}

	/* Final outcome: grey top rule */
	.doview-node--final :global(.canvas-node) {
		border-top: 3px solid #CCCCCC;
	}
</style>
