<script lang="ts">
	import { BaseEdge, EdgeReconnectAnchor, getBezierPath, type EdgeProps } from '@xyflow/svelte';

	let { id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, style, markerEnd, data }: EdgeProps = $props();

	const path = $derived(getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition }));
</script>

<BaseEdge {id} path={path[0]} {markerEnd} style={style ?? ''} aria-label="Generalization" />
<EdgeReconnectAnchor type="source" position={{ x: sourceX, y: sourceY }} />
<EdgeReconnectAnchor type="target" position={{ x: targetX, y: targetY }} />
