<script lang="ts">
	/**
	 * NavigationCellNode: Renders Prolaborate NavigationCell elements as
	 * clickable card/tile nodes that link to other diagrams.
	 *
	 * EA/Prolaborate displays these as large tiles with an icon (from the
	 * Prolaborate icon library, referenced by NID in StyleEx) and a title.
	 * The NID is parsed during import and stored as navIconId in node data.
	 */
	import { Handle, Position } from '@xyflow/svelte';
	import type { CanvasNodeData, IconRef } from '$lib/types/canvas';
	import { nodeOverrideStyle } from '$lib/canvas/utils/visualStyles';
	import IconDisplay from '$lib/icons/IconDisplay.svelte';

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
	const navIconId = $derived((data as Record<string, unknown>).navIconId as string | undefined);
	const iconRef = $derived(data.visual?.icon as IconRef | undefined);
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
		{#if iconRef}
			<IconDisplay icon={iconRef} size={48} color="#5b9bd5" />
		{:else if navIconId === '2-45' || navIconId === '2-88'}
			<!-- Person/stakeholder icon -->
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="48" height="48" class="nav-cell__nid-icon">
				<circle cx="32" cy="18" r="10" fill="#5b9bd5" opacity="0.8"/>
				<path d="M16 52c0-10 7-18 16-18s16 8 16 18" fill="#5b9bd5" opacity="0.6"/>
			</svg>
		{:else if navIconId === '2-46'}
			<!-- Computer/application icon -->
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="48" height="48" class="nav-cell__nid-icon">
				<rect x="8" y="8" width="48" height="34" rx="3" fill="#5b9bd5" opacity="0.7"/>
				<rect x="12" y="12" width="40" height="26" rx="1" fill="#fff" opacity="0.9"/>
				<rect x="24" y="44" width="16" height="4" fill="#5b9bd5" opacity="0.5"/>
				<rect x="18" y="48" width="28" height="3" rx="1" fill="#5b9bd5" opacity="0.4"/>
			</svg>
		{:else if navIconId === '2-56'}
			<!-- Building/organization icon -->
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="48" height="48" class="nav-cell__nid-icon">
				<rect x="14" y="16" width="36" height="40" fill="#5b9bd5" opacity="0.7"/>
				<rect x="8" y="12" width="48" height="6" fill="#5b9bd5" opacity="0.85"/>
				<rect x="20" y="22" width="8" height="6" rx="1" fill="#fff" opacity="0.8"/>
				<rect x="36" y="22" width="8" height="6" rx="1" fill="#fff" opacity="0.8"/>
				<rect x="20" y="34" width="8" height="6" rx="1" fill="#fff" opacity="0.8"/>
				<rect x="36" y="34" width="8" height="6" rx="1" fill="#fff" opacity="0.8"/>
				<rect x="26" y="44" width="12" height="12" fill="#fff" opacity="0.8"/>
			</svg>
		{:else if navIconId === '2-6'}
			<!-- Gear/service icon -->
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="48" height="48" class="nav-cell__nid-icon">
				<path d="M32 12l4 6h8l2 4-4 6 4 6-2 4h-8l-4 6-4-6h-8l-2-4 4-6-4-6 2-4h8z" fill="#5b9bd5" opacity="0.7"/>
				<circle cx="32" cy="32" r="8" fill="#fff" opacity="0.9"/>
			</svg>
		{:else if navIconId === '2-13'}
			<!-- Folder/project icon -->
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="48" height="48" class="nav-cell__nid-icon">
				<path d="M8 18h20l4-6h24v4H34l-4 6H8z" fill="#e8a838" opacity="0.8"/>
				<rect x="8" y="22" width="48" height="30" rx="2" fill="#f0c060" opacity="0.7"/>
			</svg>
		{:else if navIconId === '2-26'}
			<!-- Building blocks/capability icon -->
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="48" height="48" class="nav-cell__nid-icon">
				<rect x="8" y="34" width="16" height="16" rx="2" fill="#5b9bd5" opacity="0.6"/>
				<rect x="28" y="34" width="16" height="16" rx="2" fill="#5b9bd5" opacity="0.7"/>
				<rect x="48" y="34" width="8" height="16" rx="2" fill="#5b9bd5" opacity="0.5"/>
				<rect x="18" y="14" width="16" height="16" rx="2" fill="#5b9bd5" opacity="0.8"/>
				<rect x="38" y="14" width="16" height="16" rx="2" fill="#5b9bd5" opacity="0.65"/>
			</svg>
		{:else if navIconId === '2-49'}
			<!-- Grid/domain icon -->
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="48" height="48" class="nav-cell__nid-icon">
				<rect x="8" y="8" width="20" height="20" rx="2" fill="#5b9bd5" opacity="0.6"/>
				<rect x="36" y="8" width="20" height="20" rx="2" fill="#5b9bd5" opacity="0.7"/>
				<rect x="8" y="36" width="20" height="20" rx="2" fill="#5b9bd5" opacity="0.7"/>
				<rect x="36" y="36" width="20" height="20" rx="2" fill="#5b9bd5" opacity="0.6"/>
			</svg>
		{:else if navIconId === '2-29'}
			<!-- Chart/analytics icon -->
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="48" height="48" class="nav-cell__nid-icon">
				<rect x="12" y="36" width="10" height="18" fill="#5b9bd5" opacity="0.6"/>
				<rect x="27" y="24" width="10" height="30" fill="#5b9bd5" opacity="0.7"/>
				<rect x="42" y="14" width="10" height="40" fill="#5b9bd5" opacity="0.8"/>
				<line x1="8" y1="56" x2="56" y2="56" stroke="#5b9bd5" stroke-width="2" opacity="0.5"/>
			</svg>
		{:else if navIconId === '2-54'}
			<!-- List/inventory icon -->
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="48" height="48" class="nav-cell__nid-icon">
				<rect x="8" y="10" width="48" height="10" rx="2" fill="#5b9bd5" opacity="0.6"/>
				<rect x="8" y="26" width="48" height="10" rx="2" fill="#5b9bd5" opacity="0.7"/>
				<rect x="8" y="42" width="48" height="10" rx="2" fill="#5b9bd5" opacity="0.6"/>
			</svg>
		{:else}
			<!-- Fallback: generic diagram icon -->
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48" class="nav-cell__nid-icon" style="opacity:0.4">
				<rect x="4" y="4" width="40" height="34" rx="2" fill="none" stroke="currentColor" stroke-width="2"/>
				<rect x="8" y="10" width="14" height="8" rx="1" fill="currentColor" opacity="0.15"/>
				<rect x="26" y="10" width="14" height="8" rx="1" fill="currentColor" opacity="0.15"/>
				<rect x="8" y="22" width="14" height="8" rx="1" fill="currentColor" opacity="0.15"/>
				<rect x="26" y="22" width="14" height="8" rx="1" fill="currentColor" opacity="0.15"/>
			</svg>
		{/if}
	</div>
	{#if linkedModelId}
		<div class="nav-cell__link-badge" aria-label="Links to diagram">
			<!-- Small arrow icon indicating navigation link -->
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="14" height="14">
				<path d="M3 13L13 3M13 3H6M13 3v7" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
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
		border-radius: 8px;
		width: 100%;
		height: 100%;
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
	.nav-cell__nid-icon {
		max-width: 80%;
		max-height: 80%;
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
