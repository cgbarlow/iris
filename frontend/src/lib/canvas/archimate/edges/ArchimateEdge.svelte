<script lang="ts">
	/** Generic ArchiMate edge. Type-specific styling via data.archimateEdgeType. */
	import { BaseEdge, getBezierPath, type EdgeProps } from '@xyflow/svelte';

	let { id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, style, markerEnd, data }: EdgeProps = $props();

	const path = $derived(getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition }));

	const edgeType = $derived((data?.archimateEdgeType as string) ?? 'serving');

	const dashArray = $derived(
		edgeType === 'flow' || edgeType === 'access' || edgeType === 'influence'
			? '6 3'
			: edgeType === 'archimate_realization'
				? '10 5'
				: 'none',
	);
</script>

<BaseEdge {id} path={path[0]} {markerEnd} style="stroke-dasharray: {dashArray}; {style ?? ''}" aria-label="{edgeType} relationship" />
