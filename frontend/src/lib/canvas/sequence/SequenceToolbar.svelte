<script lang="ts">
	/** Zoom controls for sequence diagrams, styled to match SvelteFlow Controls. */
	interface Props {
		onzoomin: () => void;
		onzoomout: () => void;
		onfitview: () => void;
	}

	let { onzoomin, onzoomout, onfitview }: Props = $props();
</script>

<div class="svelte-flow__controls sequence-controls" role="toolbar" aria-label="Sequence diagram controls">
	<button
		onclick={onzoomin}
		class="svelte-flow__controls-button"
		aria-label="Zoom in"
		title="Zoom in"
	>
		+
	</button>
	<button
		onclick={onzoomout}
		class="svelte-flow__controls-button"
		aria-label="Zoom out"
		title="Zoom out"
	>
		&minus;
	</button>
	<button
		onclick={onfitview}
		class="svelte-flow__controls-button"
		aria-label="Fit to screen"
		title="Fit to screen"
	>
		&#x229e;
	</button>
</div>

<style>
	.sequence-controls {
		position: absolute;
		bottom: 10px;
		left: 10px;
		z-index: 5;
	}
</style>
