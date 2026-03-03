<script lang="ts">
	/**
	 * UmlEdgeRenderer: Renders edges in UML notation.
	 * Supports UML-correct dash patterns and label rendering.
	 */
	import IrisBaseEdge from '../BaseEdge.svelte';
	import type { EdgeProps } from '@xyflow/svelte';

	let props: EdgeProps = $props();

	const DASH_PATTERNS: Record<string, string> = {
		association: 'none',
		generalization: 'none',
		realization: '10 5',
		composition: 'none',
		aggregation: 'none',
		dependency: '6 3',
		usage: '6 3',
	};

	const dashArray = $derived(DASH_PATTERNS[props.data?.relationshipType ?? ''] ?? 'none');
</script>

<IrisBaseEdge {...props} {dashArray} />
