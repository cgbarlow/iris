<script lang="ts">
	/**
	 * DynamicEdge: Single edge component registered for ALL types.
	 * Reads notation from Svelte context and dispatches to the
	 * appropriate notation-specific edge renderer.
	 *
	 * Special edge types (note_link, self_loop) always use their
	 * dedicated components.
	 */
	import { getContext } from 'svelte';
	import type { EdgeProps } from '@xyflow/svelte';
	import type { NotationType } from '$lib/types/canvas';
	import NoteLinkEdge from './edges/NoteLinkEdge.svelte';
	import SelfLoopEdge from './edges/SelfLoopEdge.svelte';
	import SimpleEdgeRenderer from './renderers/SimpleEdgeRenderer.svelte';
	import UmlEdgeRenderer from './renderers/UmlEdgeRenderer.svelte';
	import ArchimateEdgeRenderer from './renderers/ArchimateEdgeRenderer.svelte';
	import IrisBaseEdge from './BaseEdge.svelte';

	let props: EdgeProps = $props();

	const notation = getContext<NotationType>('notation') ?? 'simple';

	const edgeType = $derived(props.data?.relationshipType ?? props.type ?? 'uses');
	const isNoteLink = $derived(edgeType === 'note_link');
	const isSelfLoop = $derived(props.type === 'self_loop');

	/** Simple edge relationship types. */
	const SIMPLE_TYPES = new Set(['uses', 'depends_on', 'composes', 'implements', 'contains']);

	/** UML edge relationship types. */
	const UML_TYPES = new Set(['association', 'aggregation', 'composition', 'dependency', 'realization', 'generalization', 'usage']);

	/** ArchiMate edge relationship types. */
	const ARCHIMATE_TYPES = new Set([
		'serving', 'flow', 'triggering', 'access', 'influence',
		'archimate_realization', 'archimate_composition', 'archimate_aggregation',
		'specialization', 'assignment', 'association_archimate',
	]);
</script>

{#if isSelfLoop}
	<SelfLoopEdge {...props} />
{:else if isNoteLink}
	<NoteLinkEdge {...props} />
{:else if notation === 'uml' || UML_TYPES.has(edgeType)}
	<UmlEdgeRenderer {...props} />
{:else if notation === 'archimate' || ARCHIMATE_TYPES.has(edgeType)}
	<ArchimateEdgeRenderer {...props} />
{:else if notation === 'simple' || SIMPLE_TYPES.has(edgeType)}
	<SimpleEdgeRenderer {...props} />
{:else}
	<IrisBaseEdge {...props} />
{/if}
