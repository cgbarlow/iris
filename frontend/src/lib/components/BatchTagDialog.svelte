<script lang="ts">
	import DOMPurify from 'dompurify';

	interface Props {
		open: boolean;
		onconfirm: (addTags: string[], removeTags: string[]) => void;
		oncancel: () => void;
	}

	let { open, onconfirm, oncancel }: Props = $props();

	let addInput = $state('');
	let removeInput = $state('');
	let addTags = $state<string[]>([]);
	let removeTags = $state<string[]>([]);
	let dialogEl: HTMLDialogElement | undefined = $state();

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			addTags = [];
			removeTags = [];
			addInput = '';
			removeInput = '';
			dialogEl.showModal();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	function addTag(list: 'add' | 'remove') {
		const input = list === 'add' ? addInput : removeInput;
		const tag = DOMPurify.sanitize(input.trim());
		if (!tag || tag.length > 50) return;
		if (list === 'add' && !addTags.includes(tag)) {
			addTags = [...addTags, tag];
			addInput = '';
		} else if (list === 'remove' && !removeTags.includes(tag)) {
			removeTags = [...removeTags, tag];
			removeInput = '';
		}
	}

	function removeFromList(list: 'add' | 'remove', tag: string) {
		if (list === 'add') {
			addTags = addTags.filter((t) => t !== tag);
		} else {
			removeTags = removeTags.filter((t) => t !== tag);
		}
	}

	function handleSubmit(e: Event) {
		e.preventDefault();
		onconfirm(addTags, removeTags);
	}

	function handleKeydown(e: KeyboardEvent, list: 'add' | 'remove') {
		if (e.key === 'Enter') {
			e.preventDefault();
			addTag(list);
		}
	}
</script>

<dialog
	bind:this={dialogEl}
	class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
	style="background: var(--color-bg); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 400px"
	onclose={oncancel}
>
	<h2 class="mb-4 text-lg font-semibold">Modify Tags</h2>
	<form onsubmit={handleSubmit}>
		<div class="mb-4">
			<label for="batch-add-tag" class="block text-sm font-medium">Add Tags</label>
			<div class="mt-1 flex gap-2">
				<input
					id="batch-add-tag"
					bind:value={addInput}
					onkeydown={(e) => handleKeydown(e, 'add')}
					placeholder="Tag name"
					class="flex-1 rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
				<button
					type="button"
					onclick={() => addTag('add')}
					class="rounded px-3 py-2 text-sm text-white"
					style="background-color: var(--color-primary)"
				>
					Add
				</button>
			</div>
			{#if addTags.length > 0}
				<div class="mt-2 flex flex-wrap gap-1">
					{#each addTags as tag}
						<span
							class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs text-white"
							style="background: var(--color-success)"
						>
							+{tag}
							<button
								type="button"
								onclick={() => removeFromList('add', tag)}
								class="text-white"
								aria-label="Remove {tag} from add list">&times;</button
							>
						</span>
					{/each}
				</div>
			{/if}
		</div>

		<div class="mb-4">
			<label for="batch-remove-tag" class="block text-sm font-medium">Remove Tags</label>
			<div class="mt-1 flex gap-2">
				<input
					id="batch-remove-tag"
					bind:value={removeInput}
					onkeydown={(e) => handleKeydown(e, 'remove')}
					placeholder="Tag name"
					class="flex-1 rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
				<button
					type="button"
					onclick={() => addTag('remove')}
					class="rounded px-3 py-2 text-sm text-white"
					style="background-color: var(--color-danger)"
				>
					Add
				</button>
			</div>
			{#if removeTags.length > 0}
				<div class="mt-2 flex flex-wrap gap-1">
					{#each removeTags as tag}
						<span
							class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs text-white"
							style="background: var(--color-danger)"
						>
							-{tag}
							<button
								type="button"
								onclick={() => removeFromList('remove', tag)}
								class="text-white"
								aria-label="Remove {tag} from remove list">&times;</button
							>
						</span>
					{/each}
				</div>
			{/if}
		</div>

		<div class="flex justify-end gap-3">
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
				class="rounded px-4 py-2 text-sm text-white"
				style="background-color: var(--color-primary)"
				disabled={addTags.length === 0 && removeTags.length === 0}
			>
				Apply
			</button>
		</div>
	</form>
</dialog>
