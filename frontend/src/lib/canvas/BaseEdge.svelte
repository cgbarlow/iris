<script lang="ts">
	/**
	 * BaseEdge: Shared edge logic for all canvas edge types.
	 * Handles routing type selection, EdgeLabel rendering, and reconnection anchors.
	 * Used as fallback by DynamicEdge and as foundation for edge renderers.
	 */
	import {
		BaseEdge as FlowBaseEdge,
		EdgeReconnectAnchor,
		getBezierPath,
		getStraightPath,
		getSmoothStepPath,
		type EdgeProps,
	} from '@xyflow/svelte';
	import EdgeLabel from './edges/EdgeLabel.svelte';

	interface Props extends EdgeProps {
		dashArray?: string;
	}

	let {
		id,
		sourceX,
		sourceY,
		targetX,
		targetY,
		sourcePosition,
		targetPosition,
		style,
		markerEnd,
		data,
		dashArray = 'none',
	}: Props = $props();

	const path = $derived.by(() => {
		const pathParams = { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition };
		const rt = data?.routingType;
		if (rt === 'straight') return getStraightPath(pathParams);
		if (rt === 'step') return getSmoothStepPath({ ...pathParams, borderRadius: 0 });
		if (rt === 'smoothstep') return getSmoothStepPath(pathParams);
		if (rt === 'bezier') return getBezierPath(pathParams);
		return getBezierPath(pathParams);
	});

	const edgeDash = $derived(dashArray !== 'none' ? `stroke-dasharray: ${dashArray}; ` : '');
</script>

<FlowBaseEdge
	{id}
	path={path[0]}
	{markerEnd}
	style="{edgeDash}{style ?? ''}"
	aria-label="{data?.label ?? data?.relationshipType ?? 'relationship'}"
/>
{#if data?.label}
	<EdgeLabel
		edgeId={id}
		label={data.label}
		labelX={path[1]}
		labelY={path[2]}
		offsetX={data.labelOffsetX ?? 0}
		offsetY={data.labelOffsetY ?? 0}
		rotation={data.labelRotation ?? 0}
	/>
{/if}
<EdgeReconnectAnchor type="source" position={{ x: sourceX, y: sourceY }} />
<EdgeReconnectAnchor type="target" position={{ x: targetX, y: targetY }} />
