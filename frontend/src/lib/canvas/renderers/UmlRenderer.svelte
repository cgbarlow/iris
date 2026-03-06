<script lang="ts">
	/**
	 * UmlRenderer: Renders nodes in UML notation.
	 * Supports class compartments (attributes/operations), stereotypes,
	 * abstract classes, enumerations with literals, and standard UML icons.
	 */
	import { getContext } from 'svelte';
	import { Handle, Position } from '@xyflow/svelte';
	import type { CanvasNodeData, NotationType } from '$lib/types/canvas';
	import { nodeOverrideStyle } from '$lib/canvas/utils/visualStyles';
	import { getThemeRendering } from '$lib/stores/themeStore.svelte';
	import { getActiveConfig } from '$lib/stores/viewStore.svelte';

	interface Props {
		data: CanvasNodeData;
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();

	const notation = getContext<NotationType>('notation') ?? 'uml';
	const preferredThemeId = getContext<string | undefined>('preferredThemeId');
	const rendering = $derived(getThemeRendering(notation, preferredThemeId));
	const hideIcons = $derived(rendering?.hideIcons ?? false);
	const themeBorderRadius = $derived(rendering?.borderRadius);
	const attrFontColor = $derived(rendering?.attrFontColor);
	const hideTypeStereotypes = $derived(rendering?.hideTypeStereotypes ?? false);
	const abstractBoldOverride = $derived(rendering?.abstractBoldOverride);

	const UML_ICONS: Record<string, string> = {
		class: '▭',
		object: '▯',
		use_case: '◎',
		state: '◉',
		activity: '▷',
		node: '⬡',
		interface_uml: '◯',
		enumeration: '▤',
		abstract_class: '▭',
		component_uml: '⊞',
		package_uml: '▤',
	};

	const STEREOTYPES: Record<string, string> = {
		interface_uml: 'interface',
		enumeration: 'enumeration',
		abstract_class: 'abstract',
	};

	const icon = $derived(UML_ICONS[data.entityType] ?? '▭');
	const stereotype = $derived(
		hideTypeStereotypes
			? ((data as Record<string, unknown>).stereotype as string | undefined)
			: (STEREOTYPES[data.entityType] ?? (data as Record<string, unknown>).stereotype as string | undefined)
	);
	const qualifier = $derived((data as Record<string, unknown>).qualifier as string | undefined);
	const hasCompartments = $derived(
		['class', 'abstract_class', 'interface_uml', 'enumeration'].includes(data.entityType)
	);
	const viewConfig = $derived(getActiveConfig());
	const sortAttributes = $derived(viewConfig.canvas?.sort_attributes);
	const rawAttributes = $derived((data as Record<string, unknown>).attributes as (string | { name: string; type: string; scope?: string })[] | undefined);
	const attributes = $derived.by(() => {
		if (!rawAttributes || sortAttributes !== 'alpha') return rawAttributes;
		return [...rawAttributes].sort((a, b) => {
			const nameA = typeof a === 'string' ? a : a.name;
			const nameB = typeof b === 'string' ? b : b.name;
			return nameA.localeCompare(nameB);
		});
	});
	const operations = $derived((data as Record<string, unknown>).operations as string[] | undefined);
	const literals = $derived((data as Record<string, unknown>).literals as string[] | undefined);
	const isAbstract = $derived(data.entityType === 'abstract_class');
	const isPackage = $derived(data.entityType === 'package_uml');
	const isComponent = $derived(data.entityType === 'component_uml');
	const visualStyle = $derived.by(() => {
		let style = nodeOverrideStyle(data.visual);
		if (themeBorderRadius != null) style += (style ? '; ' : '') + `border-radius: ${themeBorderRadius}px`;
		return style;
	});
</script>

<div
	class="uml-node uml-node--{data.entityType}"
	class:uml-node--selected={selected}
	class:uml-node--abstract={isAbstract}
	style={visualStyle}
	aria-label="{data.label}, {data.entityType}"
>
	{#if isPackage && !hideIcons}
		<div class="uml-node__tab">
			<span class="uml-node__icon" aria-hidden="true">{icon}</span>
		</div>
	{/if}
	<div class="uml-node__header">
		{#if !isPackage && !hideIcons}
			<span class="uml-node__icon{isComponent ? ' uml-node__icon--corner' : ''}" aria-hidden="true">{icon}</span>
		{/if}
		{#if qualifier}
			<div class="uml-node__qualifier">{qualifier}::</div>
		{/if}
		{#if stereotype}
			<div class="uml-node__stereotype">&laquo;{stereotype}&raquo;</div>
		{/if}
		<span class="uml-node__label" class:uml-node__label--underline={data.entityType === 'object'} class:uml-node__label--italic={isAbstract} class:uml-node__label--no-bold={isAbstract && abstractBoldOverride === false}>{data.label}</span>
	</div>
	{#if hasCompartments}
		{#if attributes && attributes.length > 0}
			<div class="uml-node__compartment">
				{#each attributes as attr}
					<div class="uml-node__attr" style={attrFontColor ? `color: ${attrFontColor}` : ''}>
						{#if typeof attr === 'string'}
							{attr}
						{:else}
							{attr.scope === 'Private' ? '- ' : attr.scope === 'Protected' ? '# ' : attr.scope === 'Package' ? '~ ' : '+ '}{attr.name}: {attr.type}
						{/if}
					</div>
				{/each}
			</div>
		{/if}
		{#if operations && operations.length > 0}
			<div class="uml-node__compartment">
				{#each operations as op}
					<div class="uml-node__attr">{op}</div>
				{/each}
			</div>
		{/if}
		{#if literals && literals.length > 0}
			<div class="uml-node__compartment">
				{#each literals as lit}
					<div class="uml-node__attr">{lit}</div>
				{/each}
			</div>
		{/if}
	{/if}
	{#if data.browseMode && data.entityId}
		<a href="/elements/{data.entityId}" class="canvas-node__browse-link" aria-label="View {data.label} details">
			View details
		</a>
	{/if}
	<Handle type="target" position={Position.Top} id="top" />
	<Handle type="source" position={Position.Bottom} id="bottom" />
	<Handle type="target" position={Position.Left} id="left" />
	<Handle type="source" position={Position.Right} id="right" />
	<Handle type="source" position={Position.Top} id="center" class="center-handle" style="left:50%;top:50%;transform:translate(-50%,-50%);" />
	<Handle type="target" position={Position.Top} id="center" class="center-handle" style="left:50%;top:50%;transform:translate(-50%,-50%);" />
</div>

<style>
	.uml-node {
		background: var(--color-bg, #fff);
		border: 2px solid var(--color-border, #333);
		border-radius: 3px;
		min-width: 140px;
		font-size: 0.8rem;
	}
	.uml-node--selected {
		box-shadow: 0 0 0 2px var(--color-primary, #3b82f6);
	}
	.uml-node__tab {
		position: absolute;
		top: -18px;
		left: 0;
		background: var(--color-bg, #fff);
		border: 2px solid var(--color-border, #333);
		border-bottom: none;
		padding: 1px 8px;
		font-size: 0.65rem;
		border-radius: 3px 3px 0 0;
	}
	.uml-node--package_uml {
		padding-top: 6px;
	}
	.uml-node__header {
		padding: 4px 8px;
		display: flex;
		flex-direction: column;
		align-items: center;
	}
	.uml-node__icon {
		font-size: 0.7rem;
		margin-right: 4px;
	}
	.uml-node__icon--corner {
		position: absolute;
		top: 4px;
		right: 4px;
		margin-right: 0;
	}
	.uml-node__qualifier {
		font-size: 0.6rem;
		color: var(--color-muted, #666);
	}
	.uml-node__stereotype {
		font-size: 0.65rem;
		color: var(--color-muted, #666);
	}
	.uml-node__label {
		font-weight: 700;
	}
	.uml-node__label--underline {
		text-decoration: underline;
	}
	.uml-node__label--italic {
		font-style: italic;
	}
	.uml-node__label--no-bold {
		font-weight: 400;
	}
	.uml-node__compartment {
		border-top: 1px solid var(--color-border, #333);
		padding: 4px 8px;
	}
	.uml-node__attr {
		font-size: 0.7rem;
		font-family: monospace;
	}
	:global(.dark) .uml-node {
		background: var(--color-bg, #1a1a1a);
		border-color: var(--color-border, #555);
	}
</style>
