<script lang="ts">
	/**
	 * DoviewEdgeRenderer: Renders causal_link edges in DoView notation (ADR-094).
	 * Grey (#C8C8C8), 2px stroke, straight line routing from center handles.
	 * Color is overridden via visual.lineColor if set.
	 */
	import IrisBaseEdge from '../BaseEdge.svelte';
	import type { EdgeProps } from '@xyflow/svelte';

	let props: EdgeProps = $props();

	// Force straight routing and center handles for DoView edges
	const doviewProps = $derived({
		...props,
		sourceHandleId: props.sourceHandleId || 'center',
		targetHandleId: props.targetHandleId || 'center',
		data: {
			...(props.data ?? {}),
			routingType: (props.data as Record<string, unknown>)?.routingType || 'straight',
		},
	});
</script>

<IrisBaseEdge {...doviewProps} dashArray="none" />
