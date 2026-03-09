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

	/** Derive ArchiMate layer from entityType when not explicitly set. */
	function deriveLayer(entityType: string): ArchimateLayer {
		if (entityType.startsWith('business_')) return 'business';
		if (entityType.startsWith('application_')) return 'application';
		if (entityType.startsWith('technology_')) return 'technology';
		// Motivation layer types
		if (['stakeholder', 'driver', 'assessment', 'goal', 'outcome', 'principle',
			'requirement_archimate', 'constraint_archimate'].includes(entityType)) return 'motivation';
		// Strategy layer types
		if (['resource', 'capability', 'course_of_action', 'value_stream'].includes(entityType)) return 'strategy';
		// Implementation & Migration layer types
		if (['work_package', 'deliverable', 'implementation_event', 'plateau', 'gap'].includes(entityType)) return 'implementation_migration';
		return 'business';
	}

	const layer = $derived(
		((data as Record<string, unknown>).layer as ArchimateLayer) ?? deriveLayer(data.entityType)
	);
	/**
	 * Standard ArchiMate notation icons keyed by entityType.
	 * Each value is an SVG path/content string rendered inside a 16x16 viewBox.
	 */
	const ARCHIMATE_ICONS: Record<string, string> = {
		// Business layer
		business_actor:
			'<circle cx="8" cy="4" r="2.5" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="8" y1="6.5" x2="8" y2="11" stroke="currentColor" stroke-width="1.2"/><line x1="4" y1="8" x2="12" y2="8" stroke="currentColor" stroke-width="1.2"/><line x1="8" y1="11" x2="5" y2="15" stroke="currentColor" stroke-width="1.2"/><line x1="8" y1="11" x2="11" y2="15" stroke="currentColor" stroke-width="1.2"/>',
		business_role:
			'<circle cx="8" cy="8" r="5.5" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="2.5" y1="8" x2="13.5" y2="8" stroke="currentColor" stroke-width="1.2"/>',
		business_service:
			'<rect x="1.5" y="4" width="13" height="8" rx="4" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		business_process:
			'<polygon points="1.5,4 11,4 14.5,8 11,12 1.5,12" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		business_object:
			'<rect x="2" y="2" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="2" y1="5.5" x2="14" y2="5.5" stroke="currentColor" stroke-width="1.2"/>',
		business_collaboration:
			'<circle cx="6" cy="8" r="4" fill="none" stroke="currentColor" stroke-width="1.2"/><circle cx="10" cy="8" r="4" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		business_interface:
			'<circle cx="10" cy="8" r="3.5" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="2" y1="8" x2="6.5" y2="8" stroke="currentColor" stroke-width="1.2"/>',
		business_function:
			'<polygon points="1.5,4 11,4 14.5,8 11,12 1.5,12" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		business_event:
			'<path d="M3,3 L11,3 Q14.5,8 11,13 L3,13 Q6.5,8 3,3 Z" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		// Application layer
		application_component:
			'<rect x="4" y="2" width="10" height="12" fill="none" stroke="currentColor" stroke-width="1.2"/><rect x="2" y="4.5" width="4" height="2.5" fill="none" stroke="currentColor" stroke-width="1.2"/><rect x="2" y="9" width="4" height="2.5" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		application_service:
			'<rect x="1.5" y="4" width="13" height="8" rx="4" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		application_collaboration:
			'<circle cx="6" cy="8" r="4" fill="none" stroke="currentColor" stroke-width="1.2"/><circle cx="10" cy="8" r="4" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		application_interface:
			'<circle cx="10" cy="8" r="3.5" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="2" y1="8" x2="6.5" y2="8" stroke="currentColor" stroke-width="1.2"/>',
		application_function:
			'<polygon points="1.5,4 11,4 14.5,8 11,12 1.5,12" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		application_process:
			'<polygon points="1.5,4 11,4 14.5,8 11,12 1.5,12" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		application_event:
			'<path d="M3,3 L11,3 Q14.5,8 11,13 L3,13 Q6.5,8 3,3 Z" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		data_object:
			'<rect x="2" y="2" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="2" y1="5.5" x2="14" y2="5.5" stroke="currentColor" stroke-width="1.2"/>',
		// Technology layer
		technology_service:
			'<rect x="1.5" y="4" width="13" height="8" rx="4" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		technology_collaboration:
			'<circle cx="6" cy="8" r="4" fill="none" stroke="currentColor" stroke-width="1.2"/><circle cx="10" cy="8" r="4" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		technology_interface:
			'<circle cx="10" cy="8" r="3.5" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="2" y1="8" x2="6.5" y2="8" stroke="currentColor" stroke-width="1.2"/>',
		technology_function:
			'<polygon points="1.5,4 11,4 14.5,8 11,12 1.5,12" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		technology_process:
			'<polygon points="1.5,4 11,4 14.5,8 11,12 1.5,12" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		technology_event:
			'<path d="M3,3 L11,3 Q14.5,8 11,13 L3,13 Q6.5,8 3,3 Z" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		node: '<rect x="2" y="4" width="10" height="8" fill="none" stroke="currentColor" stroke-width="1.2"/><polyline points="2,4 5,2 15,2 15,10 12,12" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="12" y1="4" x2="15" y2="2" stroke="currentColor" stroke-width="1.2"/>',
		device:
			'<rect x="2" y="3" width="12" height="8" rx="1" fill="none" stroke="currentColor" stroke-width="1.2"/><polygon points="4,11 1,14 15,14 12,11" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		artifact:
			'<polygon points="2,2 10,2 14,6 14,14 2,14" fill="none" stroke="currentColor" stroke-width="1.2"/><polyline points="10,2 10,6 14,6" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		// Strategy layer
		capability:
			'<rect x="2" y="2" width="12" height="12" rx="2" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="2" y1="6" x2="14" y2="6" stroke="currentColor" stroke-width="0.8"/><line x1="6" y1="6" x2="6" y2="14" stroke="currentColor" stroke-width="0.8"/>',
		resource:
			'<rect x="2" y="2" width="12" height="12" rx="2" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		course_of_action:
			'<circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" stroke-width="1.2"/><circle cx="8" cy="8" r="3" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		value_stream:
			'<polygon points="1.5,4 11,4 14.5,8 11,12 1.5,12" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		// Implementation & Migration layer
		work_package:
			'<rect x="2" y="2" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="2" y1="2" x2="6" y2="6" stroke="currentColor" stroke-width="1"/>',
		deliverable:
			'<rect x="2" y="2" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="2" y1="5.5" x2="14" y2="5.5" stroke="currentColor" stroke-width="1.2"/>',
		plateau:
			'<rect x="2" y="4" width="12" height="8" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="5" y1="2" x2="5" y2="4" stroke="currentColor" stroke-width="1.2"/><line x1="8" y1="2" x2="8" y2="4" stroke="currentColor" stroke-width="1.2"/><line x1="11" y1="2" x2="11" y2="4" stroke="currentColor" stroke-width="1.2"/>',
		gap: '<ellipse cx="8" cy="8" rx="6" ry="5" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="2,2"/>',
		implementation_event:
			'<path d="M3,3 L11,3 Q14.5,8 11,13 L3,13 Q6.5,8 3,3 Z" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		// Motivation layer
		stakeholder:
			'<circle cx="8" cy="4" r="2.5" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="8" y1="6.5" x2="8" y2="11" stroke="currentColor" stroke-width="1.2"/><line x1="4" y1="8" x2="12" y2="8" stroke="currentColor" stroke-width="1.2"/><line x1="8" y1="11" x2="5" y2="15" stroke="currentColor" stroke-width="1.2"/><line x1="8" y1="11" x2="11" y2="15" stroke="currentColor" stroke-width="1.2"/>',
		driver:
			'<circle cx="8" cy="8" r="5.5" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="8" y1="2.5" x2="8" y2="5" stroke="currentColor" stroke-width="1"/><line x1="8" y1="11" x2="8" y2="13.5" stroke="currentColor" stroke-width="1"/><line x1="2.5" y1="8" x2="5" y2="8" stroke="currentColor" stroke-width="1"/><line x1="11" y1="8" x2="13.5" y2="8" stroke="currentColor" stroke-width="1"/>',
		assessment:
			'<circle cx="8" cy="6" r="4" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="8" y1="10" x2="8" y2="14" stroke="currentColor" stroke-width="1.2"/><line x1="5" y1="14" x2="11" y2="14" stroke="currentColor" stroke-width="1.2"/>',
		goal: '<ellipse cx="8" cy="8" rx="6" ry="5" fill="none" stroke="currentColor" stroke-width="1.2"/><ellipse cx="8" cy="8" rx="3.5" ry="3" fill="none" stroke="currentColor" stroke-width="1"/>',
		outcome:
			'<ellipse cx="8" cy="8" rx="6" ry="5" fill="none" stroke="currentColor" stroke-width="1.2"/>',
		principle:
			'<polygon points="8,1 14.5,12 1.5,12" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="8" y1="5" x2="8" y2="9" stroke="currentColor" stroke-width="1.2"/><circle cx="8" cy="10.5" r="0.5" fill="currentColor"/>',
		requirement_archimate:
			'<ellipse cx="8" cy="8" rx="6" ry="5" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="4" y1="8" x2="12" y2="8" stroke="currentColor" stroke-width="1"/>',
		constraint_archimate:
			'<ellipse cx="8" cy="8" rx="6" ry="5" fill="none" stroke="currentColor" stroke-width="1.2"/><line x1="3" y1="5" x2="13" y2="11" stroke="currentColor" stroke-width="1"/>'
	};

	const iconSvg = $derived(ARCHIMATE_ICONS[data.entityType] ?? '');
	const hasFixedSize = $derived(data.visual?.width != null && data.visual?.height != null);
	const visualStyle = $derived.by(() => {
		let style = nodeOverrideStyle(data.visual, hasFixedSize);
		if (hasFixedSize) style += (style ? '; ' : '') + 'box-sizing: border-box';
		return style;
	});
</script>

<div
	class="archimate-node archimate-node--{layer}"
	class:archimate-node--selected={selected}
	class:archimate-node--fixed={hasFixedSize}
	style={visualStyle}
	aria-label="{data.label}, {data.entityType}"
>
	{#if iconSvg}
		<span class="archimate-node__icon" aria-hidden="true">
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="14" height="14">
				{@html iconSvg}
			</svg>
		</span>
	{/if}
	<div class="archimate-node__header">
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
	.archimate-node {
		border-radius: 4px;
		width: 100%;
		height: 100%;
		min-width: 130px;
		padding: 8px;
		border: 2px solid #666;
		font-size: 0.8rem;
		position: relative;
		box-sizing: border-box;
	}
	.archimate-node--selected {
		box-shadow: 0 0 0 2px var(--color-primary, #3b82f6);
	}
	.archimate-node__header {
		text-align: center;
	}
	.archimate-node__icon {
		position: absolute;
		top: 4px;
		right: 4px;
		display: flex;
		align-items: center;
		justify-content: center;
		opacity: 0.7;
		pointer-events: none;
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
	/* Fixed-size nodes: compact padding to fit within EA dimensions */
	.archimate-node--fixed {
		padding: 4px;
		overflow: hidden;
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
	}
	.archimate-node--fixed .archimate-node__header {
		line-height: 1.2;
	}
	.archimate-node--fixed .archimate-node__label {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		display: block;
	}
	/* Layer colours — match EA/ArchiMate standard palette */
	.archimate-node--business { background: #ffffb5; border-color: #b09a40; color: #333; }
	.archimate-node--application { background: #b5ffff; border-color: #4098ad; color: #1a4a5a; }
	.archimate-node--technology { background: #c9e7b7; border-color: #5a8a42; color: #2a4a1a; }
	.archimate-node--motivation { background: #ccccff; border-color: #7a7ab0; color: #2a2a5a; }
	.archimate-node--strategy { background: #f5deaa; border-color: #b09a40; color: #4a3a10; }
	.archimate-node--implementation_migration { background: #ffe0e0; border-color: #c07070; color: #4a1010; }
	:global(.dark) .archimate-node--business { background: #3e2723; border-color: #f9a825; }
	:global(.dark) .archimate-node--application { background: #0d47a1; border-color: #42a5f5; color: #e3f2fd; }
	:global(.dark) .archimate-node--technology { background: #1b5e20; border-color: #66bb6a; color: #e8f5e9; }
	:global(.dark) .archimate-node--motivation { background: #4a148c; border-color: #ab47bc; color: #f3e5f5; }
	:global(.dark) .archimate-node--strategy { background: #b71c1c; border-color: #ef5350; color: #ffebee; }
	:global(.dark) .archimate-node--implementation_migration { background: #212121; border-color: #bdbdbd; color: #f5f5f5; }
</style>
