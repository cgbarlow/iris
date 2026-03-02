<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';

	interface Props {
		data: { label: string; [key: string]: unknown };
		selected?: boolean;
	}

	let { data, selected = false }: Props = $props();
</script>

<div
	class="uml-node uml-node--package"
	class:uml-node--selected={selected}
	aria-label="{data.label}, Package"
>
	<div class="uml-node__tab">
		<span class="uml-node__icon" aria-hidden="true">▤</span>
	</div>
	<div class="uml-node__body">
		<span class="uml-node__label">{data.label}</span>
	</div>
	<Handle type="target" position={Position.Top} id="top" />
	<Handle type="source" position={Position.Bottom} id="bottom" />
	<Handle type="target" position={Position.Left} id="left" />
	<Handle type="source" position={Position.Right} id="right" />
	<Handle type="source" position={Position.Top} id="center" class="center-handle" style="left:50%;top:50%;transform:translate(-50%,-50%);" />
	<Handle type="target" position={Position.Top} id="center" class="center-handle" style="left:50%;top:50%;transform:translate(-50%,-50%);" />
</div>

<style>
	.uml-node--package {
		position: relative;
		min-width: 180px;
		min-height: 100px;
	}

	.uml-node__tab {
		position: absolute;
		top: -18px;
		left: 0;
		background: inherit;
		border: 1px solid var(--uml-border, #666);
		border-bottom: none;
		padding: 2px 12px;
		font-size: 0.75rem;
		border-radius: 4px 4px 0 0;
	}

	.uml-node__body {
		padding: 24px 12px 12px;
	}
</style>
