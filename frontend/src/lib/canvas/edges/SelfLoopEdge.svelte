<script lang="ts">
	import {
		BaseEdge,
		type EdgeProps,
	} from '@xyflow/svelte';
	import EdgeLabel from './EdgeLabel.svelte';

	let {
		id,
		sourceX,
		sourceY,
		targetX,
		targetY,
		style,
		markerEnd,
		data,
	}: EdgeProps = $props();

	// Cubic bezier self-loop: exits right side, curves up-right, returns to top
	const path = $derived.by(() => {
		const loopSize = 60;
		const d = `M ${sourceX} ${sourceY} C ${sourceX + loopSize} ${sourceY - loopSize}, ${targetX + loopSize} ${targetY - loopSize}, ${targetX} ${targetY}`;
		const labelX = sourceX + loopSize * 0.7;
		const labelY = sourceY - loopSize * 0.9;
		return [d, labelX, labelY] as const;
	});
</script>

<BaseEdge
	{id}
	path={path[0]}
	{markerEnd}
	style={style ?? ''}
	aria-label="{data?.label ?? 'Self'} relationship"
/>
{#if data?.label}
	<EdgeLabel edgeId={id} label={data.label} labelX={path[1]} labelY={path[2]} offsetX={data.labelOffsetX ?? 0} offsetY={data.labelOffsetY ?? 0} rotation={data.labelRotation ?? 0} />
{/if}
