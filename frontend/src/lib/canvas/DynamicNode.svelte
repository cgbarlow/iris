<script lang="ts">
	/**
	 * DynamicNode: Single node component registered for ALL types.
	 * Reads notation from Svelte context and dispatches to the
	 * appropriate notation-specific renderer.
	 *
	 * Universal types (note, boundary, modelref) always use their
	 * dedicated components regardless of notation.
	 */
	import { getContext } from 'svelte';
	import type { CanvasNodeData, NotationType } from '$lib/types/canvas';
	import NoteNode from './nodes/NoteNode.svelte';
	import BoundaryNode from './nodes/BoundaryNode.svelte';
	import ModelRefNode from './nodes/ModelRefNode.svelte';
	import SimpleRenderer from './renderers/SimpleRenderer.svelte';
	import UmlRenderer from './renderers/UmlRenderer.svelte';
	import ArchimateRenderer from './renderers/ArchimateRenderer.svelte';
	import BaseNode from './BaseNode.svelte';

	interface Props {
		data: CanvasNodeData;
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();

	const notation = getContext<NotationType>('notation') ?? 'simple';

	/** Universal types that render the same regardless of notation. */
	const UNIVERSAL_TYPES = ['note', 'boundary', 'modelref'] as const;

	const isUniversal = $derived(UNIVERSAL_TYPES.includes(data.entityType as typeof UNIVERSAL_TYPES[number]));

	/** UML type keys that should use UmlRenderer. */
	const UML_TYPES = new Set([
		'class', 'object', 'use_case', 'state', 'activity', 'node',
		'interface_uml', 'enumeration', 'abstract_class', 'component_uml', 'package_uml',
	]);

	/** ArchiMate type keys that should use ArchimateRenderer. */
	const ARCHIMATE_TYPES = new Set([
		'business_actor', 'business_role', 'business_process', 'business_service',
		'business_object', 'business_function', 'business_interaction', 'business_event',
		'business_collaboration', 'business_interface',
		'application_component', 'application_service', 'application_interface',
		'application_function', 'application_interaction', 'application_event',
		'application_collaboration', 'application_process',
		'technology_node', 'technology_service', 'technology_interface',
		'technology_function', 'technology_interaction', 'technology_event',
		'technology_collaboration', 'technology_process', 'technology_artifact',
		'technology_device',
		'stakeholder', 'driver', 'assessment', 'goal', 'outcome', 'principle',
		'requirement_archimate', 'constraint_archimate',
		'resource', 'capability', 'course_of_action', 'value_stream',
		'work_package', 'deliverable', 'implementation_event', 'plateau', 'gap',
	]);
</script>

{#if data.entityType === 'note'}
	<NoteNode {data} {selected} />
{:else if data.entityType === 'boundary'}
	<BoundaryNode {data} {selected} />
{:else if data.entityType === 'modelref'}
	<ModelRefNode {data} {selected} />
{:else if notation === 'uml' || (!isUniversal && UML_TYPES.has(data.entityType))}
	<UmlRenderer {data} {selected} />
{:else if notation === 'archimate' || ARCHIMATE_TYPES.has(data.entityType)}
	<ArchimateRenderer {data} {selected} />
{:else if notation === 'simple'}
	<SimpleRenderer {data} {selected} />
{:else}
	<!-- Fallback for unknown type/notation combinations -->
	<BaseNode {data} {selected} />
{/if}
