<script lang="ts">
	/** Dialog for creating/editing entities on the canvas. */
	import DOMPurify from 'dompurify';
	import { SIMPLE_ENTITY_TYPES, type SimpleEntityType } from '$lib/types/canvas';

	interface Props {
		open: boolean;
		mode: 'create' | 'edit';
		initialName?: string;
		initialType?: SimpleEntityType;
		initialDescription?: string;
		onsave: (name: string, type: SimpleEntityType, description: string) => void;
		oncancel: () => void;
	}

	let {
		open,
		mode,
		initialName = '',
		initialType = 'component',
		initialDescription = '',
		onsave,
		oncancel,
	}: Props = $props();

	let name = $state('');
	let entityType = $state<SimpleEntityType>('component');
	let description = $state('');
	let dialogEl: HTMLDialogElement | undefined = $state();

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			name = initialName;
			entityType = initialType;
			description = initialDescription;
			dialogEl.showModal();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		const sanitizedName = DOMPurify.sanitize(name.trim());
		const sanitizedDesc = DOMPurify.sanitize(description.trim());
		if (sanitizedName) {
			onsave(sanitizedName, entityType, sanitizedDesc);
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
		aria-labelledby="entity-dialog-title"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 360px"
	>
		<h2 id="entity-dialog-title" class="text-lg font-bold">
			{mode === 'create' ? 'Create Entity' : 'Edit Entity'}
		</h2>

		<form onsubmit={handleSubmit} class="mt-4 flex flex-col gap-4">
			<div>
				<label for="entity-name" class="block text-sm font-medium">Name</label>
				<input
					id="entity-name"
					bind:value={name}
					required
					autocomplete="off"
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
			</div>

			<div>
				<label for="entity-type" class="block text-sm font-medium">Type</label>
				<select
					id="entity-type"
					bind:value={entityType}
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				>
					{#each SIMPLE_ENTITY_TYPES as t}
						<option value={t.key}>{t.icon} {t.label}</option>
					{/each}
				</select>
			</div>

			<div>
				<label for="entity-description" class="block text-sm font-medium">Description</label>
				<textarea
					id="entity-description"
					bind:value={description}
					rows="3"
					class="mt-1 w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				></textarea>
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
					{mode === 'create' ? 'Create' : 'Save'}
				</button>
			</div>
		</form>
	</dialog>
{/if}
