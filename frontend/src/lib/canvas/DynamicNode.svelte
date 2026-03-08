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
	import type { CanvasNodeData, NotationType, NodeVisualOverrides } from '$lib/types/canvas';
	import { resolveNodeVisual } from '$lib/stores/themeStore.svelte';
	import NoteNode from './nodes/NoteNode.svelte';
	import BoundaryNode from './nodes/BoundaryNode.svelte';
	import ModelRefNode from './nodes/ModelRefNode.svelte';
	import DiagramFrameNode from './nodes/DiagramFrameNode.svelte';
	import SimpleRenderer from './renderers/SimpleRenderer.svelte';
	import UmlRenderer from './renderers/UmlRenderer.svelte';
	import ArchimateRenderer from './renderers/ArchimateRenderer.svelte';
	import C4Renderer from './renderers/C4Renderer.svelte';
	import BaseNode from './BaseNode.svelte';

	interface Props {
		data: CanvasNodeData;
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();

	const notation = getContext<NotationType>('notation') ?? 'simple';
	const preferredThemeId = getContext<string | undefined>('preferredThemeId');

	/** Compute effective visual: theme defaults merged with per-element overrides (per-element wins). */
	const effectiveData = $derived.by(() => {
		const themeVisual = resolveNodeVisual(
			notation,
			data.entityType,
			(data as Record<string, unknown>).stereotype as string | undefined,
			preferredThemeId,
		);
		if (!themeVisual && !data.visual) return data;
		const merged: NodeVisualOverrides = { ...themeVisual, ...data.visual };
		return { ...data, visual: merged };
	});

	/** Universal types that render the same regardless of notation. */
	const UNIVERSAL_TYPES = ['note', 'boundary', 'modelref'] as const;

	const isUniversal = $derived(UNIVERSAL_TYPES.includes(effectiveData.entityType as typeof UNIVERSAL_TYPES[number]));

	/** UML type keys that should use UmlRenderer. */
	const UML_TYPES = new Set([
		'class', 'object', 'use_case', 'state', 'activity', 'node',
		'interface_uml', 'enumeration', 'abstract_class', 'component_uml', 'package_uml',
	]);

	/** C4 type keys that should use C4Renderer. */
	const C4_TYPES = new Set([
		'person', 'software_system', 'software_system_external', 'container',
		'c4_component', 'code_element', 'deployment_node', 'infrastructure_node',
		'container_instance',
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

{#if effectiveData.entityType === 'diagram_frame'}
	<DiagramFrameNode data={effectiveData} />
{:else if effectiveData.entityType === 'note'}
	<NoteNode data={effectiveData} {selected} />
{:else if effectiveData.entityType === 'boundary'}
	<BoundaryNode data={effectiveData} {selected} />
{:else if effectiveData.entityType === 'modelref'}
	<ModelRefNode data={effectiveData} {selected} />
{:else if !isUniversal && ARCHIMATE_TYPES.has(effectiveData.entityType)}
	<ArchimateRenderer data={effectiveData} {selected} />
{:else if notation === 'uml' || (!isUniversal && UML_TYPES.has(effectiveData.entityType))}
	<UmlRenderer data={effectiveData} {selected} />
{:else if notation === 'c4' || C4_TYPES.has(effectiveData.entityType)}
	<C4Renderer data={effectiveData} {selected} />
{:else if notation === 'archimate'}
	<ArchimateRenderer data={effectiveData} {selected} />
{:else if notation === 'simple'}
	<SimpleRenderer data={effectiveData} {selected} />
{:else}
	<!-- Fallback for unknown type/notation combinations -->
	<BaseNode data={effectiveData} {selected} />
{/if}
