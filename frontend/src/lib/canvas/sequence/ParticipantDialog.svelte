<script lang="ts">
	/** Dialog for creating participants in a sequence diagram. */
	import DOMPurify from 'dompurify';
	import type { Participant } from './types';

	interface Props {
		open: boolean;
		onsave: (name: string, type: Participant['type']) => void;
		oncancel: () => void;
	}

	let { open, onsave, oncancel }: Props = $props();

	let name = $state('');
	let participantType = $state<Participant['type']>('component');
	let dialogEl: HTMLDialogElement | undefined = $state();

	const typeOptions: { key: Participant['type']; label: string }[] = [
		{ key: 'actor', label: 'Actor' },
		{ key: 'component', label: 'Component' },
		{ key: 'service', label: 'Service' },
	];

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			name = '';
			participantType = 'component';
			dialogEl.showModal();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		const sanitizedName = DOMPurify.sanitize(name.trim());
		if (sanitizedName) {
			onsave(sanitizedName, participantType);
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
		aria-labelledby="participant-dialog-title"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 360px"
	>
		<h2 id="participant-dialog-title" class="text-lg font-bold">Add Participant</h2>

		<form onsubmit={handleSubmit} class="mt-4 flex flex-col gap-4">
			<div>
				<label for="participant-name" class="block text-sm font-medium">Name</label>
				<input
					id="participant-name"
					bind:value={name}
					required
					autocomplete="off"
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
			</div>

			<div>
				<label for="participant-type" class="block text-sm font-medium">Type</label>
				<select
					id="participant-type"
					bind:value={participantType}
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				>
					{#each typeOptions as t}
						<option value={t.key}>{t.label}</option>
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
				>
					Add
				</button>
			</div>
		</form>
	</dialog>
{/if}
