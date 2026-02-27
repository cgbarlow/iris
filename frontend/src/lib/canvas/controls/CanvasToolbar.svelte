<script lang="ts">
	/** Canvas toolbar with zoom controls and fit-to-screen. */

	interface Props {
		onzoomin: () => void;
		onzoomout: () => void;
		onfit: () => void;
	}

	let { onzoomin, onzoomout, onfit }: Props = $props();
</script>

<div class="canvas-toolbar" role="toolbar" aria-label="Canvas controls">
	<button
		onclick={onzoomin}
		class="canvas-toolbar__btn"
		aria-label="Zoom in"
		title="Zoom in (Ctrl+=)"
	>
		+
	</button>
	<button
		onclick={onzoomout}
		class="canvas-toolbar__btn"
		aria-label="Zoom out"
		title="Zoom out (Ctrl+-)"
	>
		&minus;
	</button>
	<button
		onclick={onfit}
		class="canvas-toolbar__btn"
		aria-label="Fit to screen"
		title="Fit to screen (Ctrl+0)"
	>
		⊞
	</button>
</div>
