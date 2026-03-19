<script lang="ts">
	import {
		BaseEdge,
		type EdgeProps,
	} from '@xyflow/svelte';
	import EdgeLabel from './EdgeLabel.svelte';
	import { edgeOverrideStyle } from '$lib/canvas/utils/visualStyles';
	import type { EdgeVisualOverrides } from '$lib/types/canvas';

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

	/** Build polyline path through waypoints (90° rectangular corners). */
	function buildWaypointPath(sx: number, sy: number, tx: number, ty: number, wps: { x: number; y: number }[]): [string, number, number] {
		const points = [{ x: sx, y: sy }, ...wps, { x: tx, y: ty }];
		const d = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x},${p.y}`).join(' ');
		const mid = points[Math.floor(points.length / 2)];
		return [d, mid.x, mid.y];
	}

	const path = $derived.by(() => {
		// For self-loops with waypoints, the waypoints define the COMPLETE path (exit→around→entry).
		// SvelteFlow's sourceX/Y and targetX/Y point to handle positions that don't match EA's
		// exit/entry points, so we use ONLY the waypoints as the path.
		const waypoints = data?.waypoints as { x: number; y: number }[] | undefined;
		if (waypoints && waypoints.length >= 2) {
			const d = waypoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x},${p.y}`).join(' ');
			const mid = waypoints[Math.floor(waypoints.length / 2)];
			return [d, mid.x, mid.y] as const;
		}

		// Fallback: cubic bezier self-loop when no waypoints available
		const loopSize = 60;
		const d = `M ${sourceX} ${sourceY} C ${sourceX + loopSize} ${sourceY - loopSize}, ${targetX + loopSize} ${targetY - loopSize}, ${targetX} ${targetY}`;
		const labelX = sourceX + loopSize * 0.7;
		const labelY = sourceY - loopSize * 0.9;
		return [d, labelX, labelY] as const;
	});

	const edgeVisual = $derived(data?.visual as EdgeVisualOverrides | undefined);
	const visualOverride = $derived(edgeOverrideStyle(edgeVisual));
	const dashFromVisual = $derived(edgeVisual?.dashArray ? `stroke-dasharray: ${edgeVisual.dashArray}; ` : '');
</script>

<BaseEdge
	{id}
	path={path[0]}
	{markerEnd}
	style="{dashFromVisual}{visualOverride ? visualOverride + '; ' : ''}{style ?? ''}"
	aria-label="{data?.label ?? 'Self'} relationship"
/>
{#if data?.label}
	<EdgeLabel edgeId={id} label={data.label} labelX={path[1]} labelY={path[2]} offsetX={data.labelOffsetX ?? 0} offsetY={data.labelOffsetY ?? 0} rotation={data.labelRotation ?? 0} />
{/if}
