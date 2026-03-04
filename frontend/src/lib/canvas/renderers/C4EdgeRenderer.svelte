<script lang="ts">
	/**
	 * C4EdgeRenderer: Renders edges in C4 notation.
	 * Simple labeled arrows with optional technology annotation.
	 * All C4 relationships use solid lines.
	 */
	import IrisBaseEdge from '../BaseEdge.svelte';
	import type { EdgeProps } from '@xyflow/svelte';

	let props: EdgeProps = $props();

	/** C4 uses solid lines for all relationships. */
	const dashArray = 'none';
</script>

<IrisBaseEdge {...props} {dashArray} />
