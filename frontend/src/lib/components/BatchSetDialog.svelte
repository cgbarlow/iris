<script lang="ts">
	import { apiFetch } from '$lib/utils/api';
	import type { IrisSet } from '$lib/types/api';

	interface Props {
		open: boolean;
		onconfirm: (setId: string) => void;
		oncancel: () => void;
	}

	let { open, onconfirm, oncancel }: Props = $props();

	let sets = $state<IrisSet[]>([]);
	let selectedSetId = $state('');
	let dialogEl: HTMLDialogElement | undefined = $state();

	async function loadSets() {
		try {
			const data = await apiFetch<{ items: IrisSet[] }>('/api/sets');
			sets = data.items;
			if (sets.length > 0 && !selectedSetId) {
				selectedSetId = sets[0].id;
			}
		} catch {
			sets = [];
		}
	}

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			loadSets();
			dialogEl.showModal();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	function handleSubmit(e: Event) {
		e.preventDefault();
		if (selectedSetId) {
			onconfirm(selectedSetId);
		}
	}
</script>

<dialog
	bind:this={dialogEl}
	class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
	style="background: var(--color-bg); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 360px"
	onclose={oncancel}
>
	<h2 class="mb-4 text-lg font-semibold">Move to Set</h2>
	<form onsubmit={handleSubmit}>
		<div class="mb-4">
			<label for="batch-set-select" class="block text-sm font-medium">Target Set</label>
			<select
				id="batch-set-select"
				bind:value={selectedSetId}
				class="mt-1 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			>
				{#each sets as s}
					<option value={s.id}>{s.name}</option>
				{/each}
			</select>
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
				disabled={!selectedSetId}
			>
				Move
			</button>
		</div>
	</form>
</dialog>
