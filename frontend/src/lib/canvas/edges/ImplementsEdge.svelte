<script lang="ts">
	import {
		BaseEdge,
		EdgeReconnectAnchor,
		getBezierPath,
		getStraightPath,
		getSmoothStepPath,
		type EdgeProps,
	} from '@xyflow/svelte';
	import EdgeLabel from './EdgeLabel.svelte';

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
	}: EdgeProps = $props();

	const path = $derived.by(() => {
		const pathParams = { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition };
		const rt = data?.routingType;
		if (rt === 'straight') return getStraightPath(pathParams);
		if (rt === 'step') return getSmoothStepPath({ ...pathParams, borderRadius: 0 });
		if (rt === 'smoothstep') return getSmoothStepPath(pathParams);
		if (rt === 'bezier') return getBezierPath(pathParams);
		return getBezierPath(pathParams);
	});
</script>

<BaseEdge
	{id}
	path={path[0]}
	{markerEnd}
	style="stroke-dasharray: 10 5; {style ?? ''}"
	aria-label="{data?.label ?? 'Implements'} relationship"
/>
{#if data?.label}
	<EdgeLabel edgeId={id} label={data.label} labelX={path[1]} labelY={path[2]} offsetX={data.labelOffsetX ?? 0} offsetY={data.labelOffsetY ?? 0} rotation={data.labelRotation ?? 0} />
{/if}
<EdgeReconnectAnchor type="source" position={{ x: sourceX, y: sourceY }} />
<EdgeReconnectAnchor type="target" position={{ x: targetX, y: targetY }} />
