<script lang="ts">
	/** Dialog for configuring a relationship between two entities. */
	import { SIMPLE_RELATIONSHIP_TYPES, type SimpleRelationshipType } from '$lib/types/canvas';

	interface Props {
		open: boolean;
		sourceName: string;
		targetName: string;
		onsave: (type: SimpleRelationshipType, label: string) => void;
		oncancel: () => void;
	}

	let { open, sourceName, targetName, onsave, oncancel }: Props = $props();

	let relationshipType = $state<SimpleRelationshipType>('uses');
	let label = $state('');
	let dialogEl: HTMLDialogElement | undefined = $state();

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			relationshipType = 'uses';
			label = '';
			dialogEl.showModal();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		onsave(relationshipType, label.trim());
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
		aria-labelledby="relationship-dialog-title"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 360px"
	>
		<h2 id="relationship-dialog-title" class="text-lg font-bold">Create Relationship</h2>

		<p class="mt-2 text-sm" style="color: var(--color-muted)">
			From <strong>{sourceName}</strong> to <strong>{targetName}</strong>
		</p>

		<form onsubmit={handleSubmit} class="mt-4 flex flex-col gap-4">
			<div>
				<label for="relationship-type" class="block text-sm font-medium">Type</label>
				<select
					id="relationship-type"
					bind:value={relationshipType}
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				>
					{#each SIMPLE_RELATIONSHIP_TYPES as t}
						<option value={t.key}>{t.label} — {t.description}</option>
					{/each}
				</select>
			</div>

			<div>
				<label for="relationship-label" class="block text-sm font-medium">Label (optional)</label>
				<input
					id="relationship-label"
					bind:value={label}
					autocomplete="off"
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
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
				>
					Create
				</button>
			</div>
		</form>
	</dialog>
{/if}
