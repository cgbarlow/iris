<script lang="ts">
	/** Dialog for creating messages in a sequence diagram. */
	import DOMPurify from 'dompurify';
	import type { Participant, SequenceMessage } from './types';

	interface Props {
		open: boolean;
		participants: Participant[];
		onsave: (from: string, to: string, label: string, type: SequenceMessage['type']) => void;
		oncancel: () => void;
	}

	let { open, participants, onsave, oncancel }: Props = $props();

	let fromId = $state('');
	let toId = $state('');
	let label = $state('');
	let messageType = $state<SequenceMessage['type']>('sync');
	let dialogEl: HTMLDialogElement | undefined = $state();

	const typeOptions: { key: SequenceMessage['type']; label: string }[] = [
		{ key: 'sync', label: 'Synchronous' },
		{ key: 'async', label: 'Asynchronous' },
		{ key: 'reply', label: 'Reply' },
	];

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			fromId = participants[0]?.id ?? '';
			toId = participants[1]?.id ?? participants[0]?.id ?? '';
			label = '';
			messageType = 'sync';
			dialogEl.showModal();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		const sanitizedLabel = DOMPurify.sanitize(label.trim());
		if (sanitizedLabel && fromId && toId) {
			onsave(fromId, toId, sanitizedLabel, messageType);
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
		aria-labelledby="message-dialog-title"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 360px"
	>
		<h2 id="message-dialog-title" class="text-lg font-bold">Add Message</h2>

		<form onsubmit={handleSubmit} class="mt-4 flex flex-col gap-4">
			<div>
				<label for="message-from" class="block text-sm font-medium">From</label>
				<select
					id="message-from"
					bind:value={fromId}
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				>
					{#each participants as p}
						<option value={p.id}>{p.name}</option>
					{/each}
				</select>
			</div>

			<div>
				<label for="message-to" class="block text-sm font-medium">To</label>
				<select
					id="message-to"
					bind:value={toId}
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				>
					{#each participants as p}
						<option value={p.id}>{p.name}</option>
					{/each}
				</select>
			</div>

			<div>
				<label for="message-label" class="block text-sm font-medium">Label</label>
				<input
					id="message-label"
					bind:value={label}
					required
					autocomplete="off"
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
			</div>

			<div>
				<label for="message-type" class="block text-sm font-medium">Type</label>
				<select
					id="message-type"
					bind:value={messageType}
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
