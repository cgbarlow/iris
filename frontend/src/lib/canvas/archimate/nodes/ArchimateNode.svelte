<script lang="ts">
	/** Generic ArchiMate node component. Layer determines visual style. */
	import { Handle, Position } from '@xyflow/svelte';
	import type { ArchimateLayer } from '$lib/types/canvas';

	interface Props {
		data: {
			label: string;
			layer?: ArchimateLayer;
			icon?: string;
			archimateType?: string;
			[key: string]: unknown;
		};
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();

	const layerClass = $derived(`archimate-node--${data.layer ?? 'business'}`);
</script>

<div
	class="archimate-node {layerClass}"
	class:archimate-node--selected={selected}
	aria-label="{data.label}, {data.archimateType ?? 'ArchiMate element'}, {data.layer ?? 'business'} layer"
>
	<div class="archimate-node__header">
		{#if data.icon}
			<span class="archimate-node__icon" aria-hidden="true">{data.icon}</span>
		{/if}
		<span class="archimate-node__label">{data.label}</span>
	</div>
	<div class="archimate-node__layer-badge" aria-hidden="true">
		{(data.layer ?? 'business').charAt(0).toUpperCase()}
	</div>
	<Handle type="target" position={Position.Top} />
	<Handle type="source" position={Position.Bottom} />
</div>
