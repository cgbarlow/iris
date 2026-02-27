<script lang="ts">
	/** Accessible confirmation dialog with focus trapping. */

	interface Props {
		open: boolean;
		title: string;
		message: string;
		confirmLabel?: string;
		cancelLabel?: string;
		onconfirm: () => void;
		oncancel: () => void;
	}

	let {
		open,
		title,
		message,
		confirmLabel = 'Confirm',
		cancelLabel = 'Cancel',
		onconfirm,
		oncancel,
	}: Props = $props();

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
		aria-labelledby="confirm-title"
		aria-describedby="confirm-message"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border)"
	>
		<h2 id="confirm-title" class="text-lg font-bold">{title}</h2>
		<p id="confirm-message" class="mt-2" style="color: var(--color-muted)">{message}</p>

		<div class="mt-6 flex justify-end gap-3">
			<button
				onclick={oncancel}
				class="rounded px-4 py-2 text-sm"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				{cancelLabel}
			</button>
			<button
				onclick={onconfirm}
				class="rounded px-4 py-2 text-sm text-white"
				style="background-color: var(--color-danger)"
			>
				{confirmLabel}
			</button>
		</div>
	</dialog>
{/if}
