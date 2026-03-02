<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';

	interface Props {
		data: {
			label: string;
			literals?: string[];
			[key: string]: unknown;
		};
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();
</script>

<div
	class="uml-node uml-node--enumeration"
	class:uml-node--selected={selected}
	aria-label="{data.label}, Enumeration"
>
	<div class="uml-node__header">
		<span class="uml-node__icon" aria-hidden="true">▤</span>
		<div class="uml-node__title-block">
			<span class="uml-node__stereotype">&laquo;enumeration&raquo;</span>
			<span class="uml-node__label">{data.label}</span>
		</div>
	</div>
	{#if data.literals && data.literals.length > 0}
		<div class="uml-node__compartment">
			{#each data.literals as literal}
				<div class="uml-node__item">{literal}</div>
			{/each}
		</div>
	{/if}
	<Handle type="target" position={Position.Top} id="top" />
	<Handle type="source" position={Position.Bottom} id="bottom" />
	<Handle type="target" position={Position.Left} id="left" />
	<Handle type="source" position={Position.Right} id="right" />
	<Handle type="source" position={Position.Top} id="center" class="center-handle" style="left:50%;top:50%;transform:translate(-50%,-50%);" />
	<Handle type="target" position={Position.Top} id="center" class="center-handle" style="left:50%;top:50%;transform:translate(-50%,-50%);" />
</div>
