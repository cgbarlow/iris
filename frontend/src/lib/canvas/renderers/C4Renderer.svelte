<script lang="ts">
	/**
	 * C4Renderer: Renders nodes in C4 notation.
	 * Uses inline SVG glyphs (C4TypeGlyph) for type indicators with canonical
	 * C4 colours from the theme system (ADR-092).
	 */
	import BaseNode from '../BaseNode.svelte';
	import type { CanvasNodeData } from '$lib/types/canvas';
	import C4TypeGlyph from '$lib/c4/C4TypeGlyph.svelte';

	interface Props {
		data: CanvasNodeData;
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();

	const C4_LEVELS: Record<string, string> = {
		person: 'Person',
		software_system: 'System',
		software_system_external: 'External System',
		container: 'Container',
		c4_component: 'Component',
		code_element: 'Code',
		deployment_node: 'Deployment Node',
		infrastructure_node: 'Infrastructure',
		container_instance: 'Container Instance',
	};

	const levelLabel = $derived(C4_LEVELS[data.entityType] ?? 'Element');
</script>

{#snippet c4Icon()}
	<span class="canvas-node__icon" aria-hidden="true">
		<C4TypeGlyph type={data.entityType} size={14} color="currentColor" />
	</span>
{/snippet}

<BaseNode {data} {selected} iconSnippet={c4Icon} typeLabel={levelLabel} cssClass="c4-node c4-node--{data.entityType}" />

<style>
	:global(.c4-node) { border-radius: 8px; }

	/* Override description text color so it inherits from the node color instead
	   of using --color-muted (grey on dark backgrounds is illegible). */
	:global(.c4-node .canvas-node__description) { color: inherit; opacity: 0.85; }
</style>
