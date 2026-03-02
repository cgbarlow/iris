<script lang="ts">
	interface Props {
		selectedCount: number;
		ondelete: () => void;
		onclone: () => void;
		onmoveset: () => void;
		ontags: () => void;
		oncancel: () => void;
	}

	let { selectedCount, ondelete, onclone, onmoveset, ontags, oncancel }: Props = $props();
</script>

<div
	class="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-between border-t px-6 py-3 shadow-lg"
	style="background: var(--color-surface); border-color: var(--color-border)"
	role="toolbar"
	aria-label="Batch actions"
>
	<span class="text-sm font-medium" style="color: var(--color-fg)">
		{selectedCount} item{selectedCount !== 1 ? 's' : ''} selected
	</span>

	<div class="flex items-center gap-2">
		<button
			onclick={onclone}
			class="rounded border px-3 py-1.5 text-sm"
			style="border-color: var(--color-border); color: var(--color-fg)"
		>
			Clone
		</button>
		<button
			onclick={onmoveset}
			class="rounded border px-3 py-1.5 text-sm"
			style="border-color: var(--color-border); color: var(--color-fg)"
		>
			Move to Set
		</button>
		<button
			onclick={ontags}
			class="rounded border px-3 py-1.5 text-sm"
			style="border-color: var(--color-border); color: var(--color-fg)"
		>
			Tags
		</button>
		<button
			onclick={ondelete}
			class="rounded border px-3 py-1.5 text-sm"
			style="border-color: var(--color-border); color: var(--color-danger)"
		>
			Delete
		</button>
		<button
			onclick={oncancel}
			class="rounded border px-3 py-1.5 text-sm"
			style="border-color: var(--color-border); color: var(--color-muted)"
		>
			Cancel
		</button>
	</div>
</div>
