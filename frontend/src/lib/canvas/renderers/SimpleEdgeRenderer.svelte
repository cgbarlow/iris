<script lang="ts">
	/**
	 * SimpleEdgeRenderer: Renders edges in Simple View notation.
	 * Each relationship type gets a specific dash pattern.
	 */
	import IrisBaseEdge from '../BaseEdge.svelte';
	import type { EdgeProps } from '@xyflow/svelte';

	let props: EdgeProps = $props();

	const DASH_PATTERNS: Record<string, string> = {
		uses: '6 3',
		depends_on: '8 4',
		composes: 'none',
		implements: '10 5',
		contains: '3 3',
	};

	const dashArray = $derived(DASH_PATTERNS[props.data?.relationshipType ?? ''] ?? 'none');
</script>

<IrisBaseEdge {...props} {dashArray} />
