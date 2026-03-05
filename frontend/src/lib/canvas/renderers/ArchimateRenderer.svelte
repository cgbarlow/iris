<script lang="ts">
	/**
	 * ArchimateRenderer: Renders nodes in ArchiMate notation.
	 * Uses layer-based colour coding (business=yellow, application=blue,
	 * technology=green, motivation=purple, strategy=red, implementation=grey).
	 */
	import { Handle, Position } from '@xyflow/svelte';
	import type { CanvasNodeData, ArchimateLayer } from '$lib/types/canvas';
	import { nodeOverrideStyle } from '$lib/canvas/utils/visualStyles';

	interface Props {
		data: CanvasNodeData;
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();

	const layer = $derived(((data as Record<string, unknown>).layer as ArchimateLayer) ?? 'business');
	const archimateIcon = $derived(((data as Record<string, unknown>).icon as string) ?? '⬡');
	const visualStyle = $derived(nodeOverrideStyle(data.visual));
</script>

<div
	class="archimate-node archimate-node--{layer}"
	class:archimate-node--selected={selected}
	style={visualStyle}
	aria-label="{data.label}, {data.entityType}"
>
	<div class="archimate-node__layer-badge">{layer}</div>
	<div class="archimate-node__header">
		<span class="archimate-node__icon" aria-hidden="true">{archimateIcon}</span>
		<span class="archimate-node__label">{data.label}</span>
	</div>
	{#if data.description}
		<div class="archimate-node__description">{data.description}</div>
	{/if}
	{#if data.browseMode && data.entityId}
		<a href="/elements/{data.entityId}" class="canvas-node__browse-link" aria-label="View {data.label} details">
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
	.archimate-node {
		border-radius: 4px;
		min-width: 130px;
		padding: 8px;
		border: 2px solid #666;
		font-size: 0.8rem;
		position: relative;
	}
	.archimate-node--selected {
		box-shadow: 0 0 0 2px var(--color-primary, #3b82f6);
	}
	.archimate-node__layer-badge {
		position: absolute;
		top: -8px;
		right: 8px;
		font-size: 0.55rem;
		text-transform: uppercase;
		letter-spacing: 0.5px;
		padding: 0 4px;
		border-radius: 2px;
		background: inherit;
		border: 1px solid currentColor;
	}
	.archimate-node__header {
		text-align: center;
	}
	.archimate-node__icon {
		margin-right: 4px;
	}
	.archimate-node__label {
		font-weight: 600;
	}
	.archimate-node__description {
		font-size: 0.7rem;
		color: inherit;
		opacity: 0.85;
		margin-top: 4px;
	}
	/* Layer colours */
	.archimate-node--business { background: #fffde7; border-color: #f9a825; color: #5d4037; }
	.archimate-node--application { background: #e3f2fd; border-color: #1565c0; color: #0d47a1; }
	.archimate-node--technology { background: #e8f5e9; border-color: #2e7d32; color: #1b5e20; }
	.archimate-node--motivation { background: #f3e5f5; border-color: #7b1fa2; color: #4a148c; }
	.archimate-node--strategy { background: #ffebee; border-color: #c62828; color: #b71c1c; }
	.archimate-node--implementation_migration { background: #f5f5f5; border-color: #616161; color: #212121; }
	:global(.dark) .archimate-node--business { background: #3e2723; border-color: #f9a825; }
	:global(.dark) .archimate-node--application { background: #0d47a1; border-color: #42a5f5; color: #e3f2fd; }
	:global(.dark) .archimate-node--technology { background: #1b5e20; border-color: #66bb6a; color: #e8f5e9; }
	:global(.dark) .archimate-node--motivation { background: #4a148c; border-color: #ab47bc; color: #f3e5f5; }
	:global(.dark) .archimate-node--strategy { background: #b71c1c; border-color: #ef5350; color: #ffebee; }
	:global(.dark) .archimate-node--implementation_migration { background: #212121; border-color: #bdbdbd; color: #f5f5f5; }
</style>
