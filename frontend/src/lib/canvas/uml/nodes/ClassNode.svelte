<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';

	interface Props {
		data: {
			label: string;
			attributes?: string[];
			operations?: string[];
			[key: string]: unknown;
		};
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();
</script>

<div
	class="uml-node uml-node--class"
	class:uml-node--selected={selected}
	aria-label="{data.label}, Class"
>
	<div class="uml-node__header">
		<span class="uml-node__icon" aria-hidden="true">▭</span>
		<span class="uml-node__label">{data.label}</span>
	</div>
	{#if data.attributes && data.attributes.length > 0}
		<div class="uml-node__compartment">
			{#each data.attributes as attr}
				<div class="uml-node__item">{attr}</div>
			{/each}
		</div>
	{/if}
	{#if data.operations && data.operations.length > 0}
		<div class="uml-node__compartment">
			{#each data.operations as op}
				<div class="uml-node__item">{op}</div>
			{/each}
		</div>
	{/if}
	<Handle type="target" position={Position.Top} id="top" />
	<Handle type="source" position={Position.Bottom} id="bottom" />
	<Handle type="target" position={Position.Left} id="left" />
	<Handle type="source" position={Position.Right} id="right" />
</div>
