<script lang="ts">
	/** Dialog for creating a new collection. */
	import DOMPurify from 'dompurify';

	interface Props {
		open: boolean;
		oncreate: (name: string, description: string | null) => void;
		oncancel: () => void;
	}

	let { open, oncreate, oncancel }: Props = $props();

	let dialogEl: HTMLDialogElement | undefined = $state();
	let name = $state('');
	let description = $state('');

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			name = '';
			description = '';
			dialogEl.showModal();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		const sanitizedName = DOMPurify.sanitize(name.trim());
		const sanitizedDesc = description.trim()
			? DOMPurify.sanitize(description.trim())
			: null;
		if (sanitizedName) {
			oncreate(sanitizedName, sanitizedDesc);
		}
	}

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
		aria-labelledby="collection-dialog-title"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 400px"
	>
		<h2 id="collection-dialog-title" class="text-lg font-bold">New Collection</h2>

		<form onsubmit={handleSubmit} class="mt-4">
			<div>
				<label for="collection-name" class="text-sm font-medium" style="color: var(--color-fg)">
					Name <span style="color: var(--color-danger)">*</span>
				</label>
				<input
					id="collection-name"
					bind:value={name}
					type="text"
					required
					maxlength="255"
					placeholder="e.g. Programme Alpha"
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
			</div>

			<div class="mt-3">
				<label for="collection-description" class="text-sm font-medium" style="color: var(--color-fg)">
					Description
				</label>
				<textarea
					id="collection-description"
					bind:value={description}
					rows="3"
					placeholder="Optional description..."
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				></textarea>
			</div>

			<div class="mt-6 flex justify-end gap-3">
				<button
					type="button"
					onclick={oncancel}
					class="rounded px-4 py-2 text-sm"
					style="border: 1px solid var(--color-border); color: var(--color-fg)"
				>
					Cancel
				</button>
				<button
					type="submit"
					disabled={!name.trim()}
					class="rounded px-4 py-2 text-sm text-white"
					style="background-color: var(--color-primary)"
				>
					Create Collection
				</button>
			</div>
		</form>
	</dialog>
{/if}
