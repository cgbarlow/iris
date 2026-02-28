<script lang="ts">
	/** Fullscreen overlay for distraction-free canvas work. */
	import type { Snippet } from 'svelte';

	interface Props {
		onexit: () => void;
		children: Snippet;
	}

	let { onexit, children }: Props = $props();

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			event.preventDefault();
			event.stopPropagation();
			onexit();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div
	class="focus-view"
	role="dialog"
	aria-label="Focus view"
>
	<button
		onclick={onexit}
		class="focus-view__exit"
		aria-label="Exit focus view"
		title="Exit focus view (Escape)"
	>
		&times;
	</button>
	<div class="focus-view__content">
		{@render children()}
	</div>
</div>

<style>
	.focus-view {
		position: fixed;
		inset: 0;
		z-index: 50;
		background: var(--color-bg);
		display: flex;
		flex-direction: column;
	}

	.focus-view__exit {
		position: absolute;
		top: 12px;
		right: 12px;
		z-index: 51;
		width: 36px;
		height: 36px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 1px solid var(--color-border);
		border-radius: 4px;
		background: var(--color-surface);
		color: var(--color-fg);
		font-size: 1.25rem;
		cursor: pointer;
	}

	.focus-view__exit:hover {
		background: var(--color-border);
	}

	.focus-view__content {
		width: 100%;
		height: 100%;
		overflow: hidden;
	}
</style>
