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
	import EdgeEndpointLabels from './edges/EdgeEndpointLabels.svelte';
	import { edgeOverrideStyle } from '$lib/canvas/utils/visualStyles';
	import { getActiveConfig } from '$lib/stores/viewStore.svelte';
	import type { EdgeVisualOverrides, CanvasEdgeData } from '$lib/types/canvas';

	interface Props extends EdgeProps {
		dashArray?: string;
		markerStart?: string;
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
		markerStart,
		data,
		dashArray = 'none',
	}: Props = $props();

	/** Build polyline path through waypoints. */
	function buildWaypointPath(sx: number, sy: number, tx: number, ty: number, wps: { x: number; y: number }[]): [string, number, number] {
		const points = [{ x: sx, y: sy }, ...wps, { x: tx, y: ty }];
		const d = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x},${p.y}`).join(' ');
		// Label position at midpoint of path
		const mid = points[Math.floor(points.length / 2)];
		return [d, mid.x, mid.y];
	}

	const path = $derived.by(() => {
		// Use SvelteFlow's computed handle positions (correctly placed on node edges)
		let sx = sourceX, sy = sourceY, tx = targetX, ty = targetY;

		// Waypoint-based polyline routing
		const waypoints = data?.waypoints as { x: number; y: number }[] | undefined;
		if (waypoints && waypoints.length > 0) {
			return buildWaypointPath(sx, sy, tx, ty, waypoints);
		}

		const pathParams = { sourceX: sx, sourceY: sy, targetX: tx, targetY: ty, sourcePosition, targetPosition };
		const rt = data?.routingType;
		if (rt === 'straight') return getStraightPath(pathParams);
		if (rt === 'step') return getSmoothStepPath({ ...pathParams, borderRadius: 0 });
		if (rt === 'smoothstep') return getSmoothStepPath(pathParams);
		if (rt === 'bezier') return getBezierPath(pathParams);
		return getBezierPath(pathParams);
	});

	const edgeDash = $derived(dashArray !== 'none' ? `stroke-dasharray: ${dashArray}; ` : '');
	const edgeVisual = $derived(data?.visual as EdgeVisualOverrides | undefined);
	const visualOverride = $derived(edgeOverrideStyle(edgeVisual));
	const dashFromVisual = $derived(edgeVisual?.dashArray ? `stroke-dasharray: ${edgeVisual.dashArray}; ` : '');

	// ViewConfig toggles for endpoint labels (ADR-086)
	const viewConfig = $derived(getActiveConfig());
	const showCardinality = $derived(viewConfig.canvas?.show_cardinality !== false);
	const showRoleNames = $derived(viewConfig.canvas?.show_role_names !== false);
	const edgeData = $derived(data as CanvasEdgeData | undefined);
	const hasEndpointLabels = $derived(
		(showCardinality && (edgeData?.sourceCardinality || edgeData?.targetCardinality)) ||
		(showRoleNames && (edgeData?.sourceRole || edgeData?.targetRole))
	);
</script>

<FlowBaseEdge
	{id}
	path={path[0]}
	{markerEnd}
	{markerStart}
	style="{edgeDash}{dashFromVisual}{visualOverride ? visualOverride + '; ' : ''}{style ?? ''}"
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
{#if hasEndpointLabels}
	<EdgeEndpointLabels
		{sourceX} {sourceY} {targetX} {targetY}
		sourceCardinality={showCardinality ? edgeData?.sourceCardinality : undefined}
		targetCardinality={showCardinality ? edgeData?.targetCardinality : undefined}
		sourceRole={showRoleNames ? edgeData?.sourceRole : undefined}
		targetRole={showRoleNames ? edgeData?.targetRole : undefined}
		labelPositions={edgeData?.labelPositions}
	/>
{/if}
<EdgeReconnectAnchor type="source" position={{ x: sourceX, y: sourceY }} />
<EdgeReconnectAnchor type="target" position={{ x: targetX, y: targetY }} />
