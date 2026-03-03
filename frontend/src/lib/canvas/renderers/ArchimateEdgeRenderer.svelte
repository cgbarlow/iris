<script lang="ts">
	/**
	 * ArchimateEdgeRenderer: Renders edges in ArchiMate notation.
	 * Uses ArchiMate-specific dash patterns per relationship type.
	 */
	import IrisBaseEdge from '../BaseEdge.svelte';
	import type { EdgeProps } from '@xyflow/svelte';

	let props: EdgeProps = $props();

	const edgeType = $derived((props.data?.archimateEdgeType as string) ?? props.data?.relationshipType ?? 'serving');

	const DASH_PATTERNS: Record<string, string> = {
		serving: 'none',
		flow: '6 3',
		triggering: 'none',
		access: '6 3',
		influence: '6 3',
		archimate_realization: '10 5',
		archimate_composition: 'none',
		archimate_aggregation: 'none',
		specialization: 'none',
		assignment: 'none',
		association_archimate: 'none',
	};

	const dashArray = $derived(DASH_PATTERNS[edgeType] ?? 'none');
</script>

<IrisBaseEdge {...props} {dashArray} />
