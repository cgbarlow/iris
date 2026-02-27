<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';

	interface Props {
		data: { label: string; [key: string]: unknown };
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();
</script>

<div
	class="uml-node uml-node--use-case"
	class:uml-node--selected={selected}
	aria-label="{data.label}, Use Case"
>
	<div class="uml-node__header">
		<span class="uml-node__icon" aria-hidden="true">◎</span>
		<span class="uml-node__label">{data.label}</span>
	</div>
	<Handle type="target" position={Position.Top} />
	<Handle type="source" position={Position.Bottom} />
</div>
