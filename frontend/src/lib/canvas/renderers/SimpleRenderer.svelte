<script lang="ts">
	/**
	 * SimpleRenderer: Renders nodes in Simple View notation.
	 * Icon + label + optional description. Each type gets a unique icon.
	 */
	import BaseNode from '../BaseNode.svelte';
	import type { CanvasNodeData } from '$lib/types/canvas';
	import { nodeOverrideStyle } from '$lib/canvas/utils/visualStyles';

	interface Props {
		data: CanvasNodeData;
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();

	const SIMPLE_ICONS: Record<string, string> = {
		component: '⬡',
		service: '◎',
		interface: '◯',
		package: '▤',
		actor: '👤',
		database: '▦',
		queue: '≋',
	};

	const icon = $derived(SIMPLE_ICONS[data.entityType] ?? '⬡');
	const visualStyle = $derived(nodeOverrideStyle(data.visual));
</script>

<div style={visualStyle}>
	<BaseNode {data} {selected} {icon} typeLabel={data.entityType} cssClass="canvas-node--{data.entityType}" />
</div>
