<script lang="ts">
	/** Zoom controls for sequence diagrams, reusing SvelteFlow Controls styling and icons. */
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
		class="svelte-flow__controls-button svelte-flow__controls-zoomin"
		aria-label="Zoom in"
		title="Zoom in"
	>
		<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><path d="M32 18.133H18.133V32h-4.266V18.133H0v-4.266h13.867V0h4.266v13.867H32z" /></svg>
	</button>
	<button
		onclick={onzoomout}
		class="svelte-flow__controls-button svelte-flow__controls-zoomout"
		aria-label="Zoom out"
		title="Zoom out"
	>
		<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 5"><path d="M0 0h32v4.2H0z" /></svg>
	</button>
	<button
		onclick={onfitview}
		class="svelte-flow__controls-button svelte-flow__controls-fitview"
		aria-label="Fit to screen"
		title="Fit to screen"
	>
		<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 30"><path d="M3.692 4.63c0-.53.4-.938.939-.938h5.215V0H4.708C2.13 0 0 2.054 0 4.63v5.216h3.692V4.631zM27.354 0h-5.2v3.692h5.17c.53 0 .984.4.984.939v5.215H32V4.631A4.624 4.624 0 0027.354 0zm.954 24.83c0 .532-.4.94-.939.94h-5.215v3.768h5.215c2.577 0 4.631-2.13 4.631-4.707v-5.139h-3.692v5.139zm-23.677.94c-.531 0-.939-.4-.939-.94v-5.138H0v5.139c0 2.577 2.13 4.707 4.708 4.707h5.138V25.77H4.631z" /></svg>
	</button>
</div>

<style>
	.sequence-controls {
		position: absolute;
		bottom: 10px;
		left: 10px;
		z-index: 5;
		display: flex;
		flex-direction: column;
		box-shadow: 0 0 2px 1px rgba(0, 0, 0, 0.08);
	}
	.sequence-controls :global(.svelte-flow__controls-button) {
		display: flex;
		justify-content: center;
		align-items: center;
		height: 26px;
		width: 26px;
		padding: 4px;
		border: none;
		background: #fefefe;
		border-bottom: 1px solid #eee;
		color: inherit;
		cursor: pointer;
	}
	.sequence-controls :global(.svelte-flow__controls-button:hover) {
		background: #f4f4f4;
	}
	.sequence-controls :global(.svelte-flow__controls-button:last-child) {
		border-bottom: none;
	}
	.sequence-controls :global(.svelte-flow__controls-button svg) {
		width: 100%;
		max-width: 12px;
		max-height: 12px;
	}
	:global(.dark) .sequence-controls :global(.svelte-flow__controls-button) {
		background: #2b2b2b;
		border-bottom-color: #5b5b5b;
		color: #f8f8f8;
	}
	:global(.dark) .sequence-controls :global(.svelte-flow__controls-button:hover) {
		background: #3e3e3e;
		color: #fff;
	}
</style>
