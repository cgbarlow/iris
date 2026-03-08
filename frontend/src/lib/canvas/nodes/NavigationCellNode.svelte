<script lang="ts">
	/**
	 * NavigationCellNode: Renders Prolaborate NavigationCell elements as
	 * clickable card/tile nodes that link to other diagrams.
	 *
	 * In EA/Prolaborate these appear as large tiles with an image and title,
	 * plus a small navigation icon in the bottom-right corner. Since we don't
	 * have the Prolaborate-specific images, we render them as styled cards with
	 * the diagram name as title and a descriptive icon.
	 */
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
		if (hasFixedSize) style += (style ? '; ' : '') + 'box-sizing: border-box';
		return style;
	});
	const linkedModelId = $derived((data as Record<string, unknown>).linkedModelId as string | undefined);
</script>

<div
	class="nav-cell"
	class:nav-cell--selected={selected}
	class:nav-cell--fixed={hasFixedSize}
	class:nav-cell--linked={!!linkedModelId}
	style={visualStyle}
	aria-label="{data.label}, navigation cell"
>
	<div class="nav-cell__title">{data.label}</div>
	<div class="nav-cell__icon-area">
		<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48" class="nav-cell__diagram-icon">
			<rect x="4" y="4" width="40" height="34" rx="2" fill="none" stroke="currentColor" stroke-width="2" opacity="0.3"/>
			<rect x="8" y="10" width="14" height="8" rx="1" fill="currentColor" opacity="0.15"/>
			<rect x="26" y="10" width="14" height="8" rx="1" fill="currentColor" opacity="0.15"/>
			<rect x="8" y="22" width="14" height="8" rx="1" fill="currentColor" opacity="0.15"/>
			<rect x="26" y="22" width="14" height="8" rx="1" fill="currentColor" opacity="0.15"/>
			<line x1="15" y1="18" x2="33" y2="10" stroke="currentColor" stroke-width="1" opacity="0.2"/>
			<line x1="15" y1="26" x2="33" y2="22" stroke="currentColor" stroke-width="1" opacity="0.2"/>
		</svg>
	</div>
	{#if linkedModelId}
		<div class="nav-cell__link-badge" aria-label="Links to diagram">
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="14" height="14">
				<path d="M6.5 10.5L2 6l1-1 3.5 3.5L13 2l1 1z" fill="currentColor"/>
				<rect x="1" y="1" width="14" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.2"/>
			</svg>
		</div>
	{/if}
	{#if data.browseMode && data.entityId}
		<a href="/elements/{data.entityId}" class="canvas-node__browse-link" aria-label="View {data.label} details">
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
	.nav-cell {
		background: #f8f9fa;
		border: 1px solid #c0c0c0;
		border-radius: 4px;
		min-width: 140px;
		min-height: 90px;
		padding: 8px;
		display: flex;
		flex-direction: column;
		align-items: center;
		position: relative;
		cursor: default;
		box-sizing: border-box;
	}
	.nav-cell--linked {
		cursor: pointer;
	}
	.nav-cell--selected {
		box-shadow: 0 0 0 2px var(--color-primary, #3b82f6);
	}
	.nav-cell--fixed {
		min-width: 0;
		min-height: 0;
	}
	.nav-cell__title {
		font-size: 0.75rem;
		font-weight: 600;
		text-align: center;
		color: #333;
		margin-bottom: 4px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		max-width: 100%;
	}
	.nav-cell__icon-area {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		color: #888;
	}
	.nav-cell__diagram-icon {
		opacity: 0.6;
	}
	.nav-cell__link-badge {
		position: absolute;
		bottom: 4px;
		right: 4px;
		color: #6b7280;
		opacity: 0.7;
	}
	:global(.dark) .nav-cell {
		background: #1f2937;
		border-color: #4b5563;
	}
	:global(.dark) .nav-cell__title {
		color: #e5e7eb;
	}
	:global(.dark) .nav-cell__icon-area {
		color: #6b7280;
	}
</style>
