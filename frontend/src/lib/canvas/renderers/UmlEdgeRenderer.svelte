<script lang="ts">
	/**
	 * UmlEdgeRenderer: Renders edges in UML notation.
	 * Supports UML-correct dash patterns, arrowhead markers, and label rendering (ADR-086).
	 */
	import IrisBaseEdge from '../BaseEdge.svelte';
	import type { EdgeProps } from '@xyflow/svelte';
	import type { CanvasEdgeData } from '$lib/types/canvas';

	let props: EdgeProps = $props();
	const edgeData = $derived(props.data as CanvasEdgeData | undefined);

	const DASH_PATTERNS: Record<string, string> = {
		association: 'none',
		generalization: 'none',
		realization: '10 5',
		composition: 'none',
		aggregation: 'none',
		dependency: '6 3',
		usage: '6 3',
	};

	/** Marker at the target (arrow) end of the edge. */
	const MARKER_END: Record<string, string> = {
		generalization: 'url(#uml-triangle-closed)',
		realization: 'url(#uml-triangle-closed)',
		dependency: 'url(#uml-arrow-open)',
		usage: 'url(#uml-arrow-open)',
	};

	/** Marker at the source end of the edge. */
	const MARKER_START: Record<string, string> = {
		composition: 'url(#uml-diamond-filled)',
		aggregation: 'url(#uml-diamond-open)',
	};

	const relType = $derived(String(edgeData?.relationshipType ?? ''));
	const dashArray = $derived(DASH_PATTERNS[relType] ?? 'none');
	const markerEnd = $derived(
		MARKER_END[relType] ??
		(((relType === 'association' || relType === 'composition' || relType === 'aggregation') && edgeData?.direction === 'Source -> Destination') ? 'url(#uml-arrow-open)' : undefined)
	);
	const markerStart = $derived(MARKER_START[relType] ?? undefined);
</script>

<IrisBaseEdge {...props} {dashArray} {markerEnd} {markerStart} />
