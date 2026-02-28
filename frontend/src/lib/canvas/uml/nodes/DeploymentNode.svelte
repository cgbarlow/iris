<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';

	interface Props {
		data: { label: string; [key: string]: unknown };
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();
</script>

<div
	class="uml-node uml-node--deployment"
	class:uml-node--selected={selected}
	aria-label="{data.label}, Deployment Node"
>
	<div class="uml-node__header">
		<span class="uml-node__icon" aria-hidden="true">⬡</span>
		<span class="uml-node__label">{data.label}</span>
	</div>
	<Handle type="target" position={Position.Top} id="top" />
	<Handle type="source" position={Position.Bottom} id="bottom" />
	<Handle type="target" position={Position.Left} id="left" />
	<Handle type="source" position={Position.Right} id="right" />
</div>
