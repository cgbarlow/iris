<script lang="ts">
	/**
	 * C4Renderer: Renders nodes in C4 notation.
	 * Level badges, C4-style boxes, person icons.
	 * Internal systems are blue, external are grey, containers green, components orange.
	 */
	import BaseNode from '../BaseNode.svelte';
	import type { CanvasNodeData } from '$lib/types/canvas';
	import { nodeOverrideStyle } from '$lib/canvas/utils/visualStyles';

	interface Props {
		data: CanvasNodeData;
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();

	const C4_ICONS: Record<string, string> = {
		person: '👤',
		software_system: '▣',
		software_system_external: '▢',
		container: '▤',
		c4_component: '⬡',
		code_element: '▭',
		deployment_node: '⬢',
		infrastructure_node: '◆',
		container_instance: '▥',
	};

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

	const icon = $derived(C4_ICONS[data.entityType] ?? '▣');
	const levelLabel = $derived(C4_LEVELS[data.entityType] ?? 'Element');
	const visualStyle = $derived(nodeOverrideStyle(data.visual));
</script>

<div style={visualStyle}>
	<BaseNode {data} {selected} {icon} typeLabel={levelLabel} cssClass="c4-node c4-node--{data.entityType}" />
</div>

<style>
	:global(.c4-node) { border-radius: 8px; }
	:global(.c4-node--person) { background: #08427b; color: white; }
	:global(.c4-node--software_system) { background: #1168bd; color: white; }
	:global(.c4-node--software_system_external) { background: #999999; color: white; }
	:global(.c4-node--container) { background: #438dd5; color: white; }
	:global(.c4-node--c4_component) { background: #85bbf0; color: #1a1a2e; }
	:global(.c4-node--code_element) { background: #b3d7ff; color: #1a1a2e; }
	:global(.c4-node--deployment_node) { background: #ffffff; border: 2px solid #438dd5; color: #1a1a2e; }
	:global(.c4-node--infrastructure_node) { background: #ffffff; border: 2px solid #999999; color: #1a1a2e; }
	:global(.c4-node--container_instance) { background: #438dd5; color: white; border-style: dashed; }

	/* Override description text color so it inherits from the node color instead
	   of using --color-muted (grey on dark backgrounds is illegible). */
	:global(.c4-node .canvas-node__description) { color: inherit; opacity: 0.85; }

	/* Dark mode variants */
	:global(.dark) :global(.c4-node--person) { background: #0a5299; }
	:global(.dark) :global(.c4-node--software_system) { background: #1472cc; }
	:global(.dark) :global(.c4-node--software_system_external) { background: #666666; }
	:global(.dark) :global(.c4-node--container) { background: #3a7ec0; }
	:global(.dark) :global(.c4-node--c4_component) { background: #6ba3d9; color: white; }
	:global(.dark) :global(.c4-node--code_element) { background: #4a8cc7; color: white; }
	:global(.dark) :global(.c4-node--deployment_node) { background: #1e293b; border-color: #438dd5; color: #e2e8f0; }
	:global(.dark) :global(.c4-node--infrastructure_node) { background: #1e293b; border-color: #666666; color: #e2e8f0; }
	:global(.dark) :global(.c4-node--container_instance) { background: #3a7ec0; }
</style>
