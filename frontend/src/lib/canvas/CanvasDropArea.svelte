<script lang="ts">
	/**
	 * v5.3.1 hot-fix (issue #37 reopen): the drop handler that powers
	 * the BPMN palette → canvas drag-and-drop needs `useSvelteFlow()`
	 * to project the cursor coordinate. xyflow's hook reads context via
	 * `getContext` at call time, which has to be **during component
	 * initialisation** AND must be inside `<SvelteFlowProvider>` (or
	 * inside `<SvelteFlow>` itself).
	 *
	 * v5.2.0 called `useSvelteFlow()` at the script level of
	 * UnifiedCanvas — but UnifiedCanvas is also where the
	 * `<SvelteFlowProvider>` is mounted in the template, so the script
	 * ran *before* the provider existed and the hook threw
	 * "To call useStore outside of <SvelteFlow /> you need to wrap
	 * your component in a <SvelteFlowProvider />".
	 *
	 * This component is a thin descendant of SvelteFlowProvider — its
	 * script runs after the provider is set up, so `useSvelteFlow()`
	 * resolves correctly.
	 */
	import type { Snippet } from 'svelte';
	import { useSvelteFlow } from '@xyflow/svelte';

	interface Props {
		ondropentity?: (entityKey: string, position: { x: number; y: number }) => void;
		children: Snippet;
	}

	let { ondropentity, children }: Props = $props();

	const flow = useSvelteFlow();

	function handleDragOver(e: DragEvent) {
		if (e.dataTransfer?.types.includes('application/iris-bpmn-entity')) {
			e.preventDefault();
			e.dataTransfer.dropEffect = 'copy';
		}
	}

	function handleDrop(e: DragEvent) {
		const key = e.dataTransfer?.getData('application/iris-bpmn-entity');
		if (!key) return;
		e.preventDefault();
		const position = flow.screenToFlowPosition({ x: e.clientX, y: e.clientY });
		ondropentity?.(key, position);
	}
</script>

<!-- `display: contents` so this wrapper doesn't disturb the surrounding
	 layout — the drop listeners attach to a stand-in element that
	 covers the whole subtree. -->
<div
	class="canvas-drop-area"
	ondragover={handleDragOver}
	ondrop={handleDrop}
	role="presentation"
>
	{@render children()}
</div>

<style>
	.canvas-drop-area {
		display: contents;
	}
</style>
