<script lang="ts">
	/** Canvas toolbar with zoom controls and fit-to-screen.
	 *  Must be rendered inside a <SvelteFlow> slot to access the flow context.
	 */
	import { useSvelteFlow } from '@xyflow/svelte';

	interface Props {
		onannounce?: (message: string) => void;
	}

	let { onannounce }: Props = $props();

	const { fitView, zoomIn, zoomOut } = useSvelteFlow();
</script>

<div class="canvas-toolbar" role="toolbar" aria-label="Canvas controls">
	<button
		onclick={() => { zoomIn(); onannounce?.('Zoomed in'); }}
		class="canvas-toolbar__btn"
		aria-label="Zoom in"
		title="Zoom in (Ctrl+=)"
	>
		+
	</button>
	<button
		onclick={() => { zoomOut(); onannounce?.('Zoomed out'); }}
		class="canvas-toolbar__btn"
		aria-label="Zoom out"
		title="Zoom out (Ctrl+-)"
	>
		&minus;
	</button>
	<button
		onclick={() => { fitView(); onannounce?.('Fit to screen'); }}
		class="canvas-toolbar__btn"
		aria-label="Fit to screen"
		title="Fit to screen (Ctrl+0)"
	>
		⊞
	</button>
</div>
