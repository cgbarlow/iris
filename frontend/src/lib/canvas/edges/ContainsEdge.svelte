<script lang="ts">
	import { BaseEdge, getBezierPath, type EdgeProps } from '@xyflow/svelte';

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

	const path = $derived(
		getBezierPath({
			sourceX,
			sourceY,
			targetX,
			targetY,
			sourcePosition,
			targetPosition,
		}),
	);
</script>

<BaseEdge
	{id}
	path={path[0]}
	{markerEnd}
	style="stroke-dasharray: 3 3; {style ?? ''}"
	aria-label="{data?.label ?? 'Contains'} relationship"
/>
{#if data?.label}
	<text>
		<textPath
			href="#{id}"
			startOffset="50%"
			text-anchor="middle"
			dominant-baseline="text-before-edge"
			class="canvas-edge__label"
		>
			{data.label}
		</textPath>
	</text>
{/if}
