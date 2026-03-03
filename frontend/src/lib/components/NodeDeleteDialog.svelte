<script lang="ts">
	/** Dialog for removing a node from canvas or cascade-deleting the entity. */

	interface Props {
		open: boolean;
		nodeName: string;
		isModelRef: boolean;
		onremove: () => void;
		ondelete: () => void;
		oncancel: () => void;
	}

	let { open, nodeName, isModelRef, onremove, ondelete, oncancel }: Props = $props();

	let dialogEl: HTMLDialogElement | undefined = $state();

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			dialogEl.showModal();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			oncancel();
		}
	}
</script>

{#if open}
	<dialog
		bind:this={dialogEl}
		onkeydown={handleKeydown}
		aria-labelledby="node-delete-title"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 360px"
	>
		<h2 id="node-delete-title" class="text-lg font-bold">Remove "{nodeName}"</h2>

		<p class="mt-2 text-sm" style="color: var(--color-muted)">
			Choose how to handle this {isModelRef ? 'model reference' : 'entity'}:
		</p>

		<div class="mt-4 flex flex-col gap-3">
			<button
				onclick={onremove}
				class="w-full rounded border p-3 text-left text-sm hover:opacity-80"
				style="border-color: var(--color-border); color: var(--color-fg)"
			>
				<span class="font-medium">Remove from this model</span>
				<p class="mt-0.5 text-xs" style="color: var(--color-muted)">
					Removes the node from this canvas only. The {isModelRef ? 'model' : 'entity'} remains in the system.
				</p>
			</button>

			{#if !isModelRef}
				<button
					onclick={ondelete}
					class="w-full rounded border p-3 text-left text-sm hover:opacity-80"
					style="border-color: var(--color-danger, #dc2626); color: var(--color-danger, #dc2626)"
				>
					<span class="font-medium">Delete entity and all relationships</span>
					<p class="mt-0.5 text-xs" style="color: var(--color-muted)">
						Permanently deletes this entity from all models and removes all its relationships.
					</p>
				</button>
			{/if}
		</div>

		<div class="mt-4 flex justify-end">
			<button
				type="button"
				onclick={oncancel}
				class="rounded px-4 py-2 text-sm"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				Cancel
			</button>
		</div>
	</dialog>
{/if}
