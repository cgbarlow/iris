<script lang="ts">
	/**
	 * Searchable entity picker dialog for linking existing entities to a canvas.
	 */
	import { apiFetch } from '$lib/utils/api';
	import type { Entity, PaginatedResponse } from '$lib/types/api';

	interface Props {
		open: boolean;
		onselect: (entity: Entity) => void;
		oncancel: () => void;
	}

	let { open, onselect, oncancel }: Props = $props();

	let entities = $state<Entity[]>([]);
	let search = $state('');
	let loading = $state(false);
	let dialogEl: HTMLDialogElement | undefined = $state();

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			search = '';
			dialogEl.showModal();
			loadEntities();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	async function loadEntities() {
		loading = true;
		try {
			const data = await apiFetch<PaginatedResponse<Entity>>('/api/entities');
			entities = data.items.filter((e) => !e.is_deleted);
		} catch {
			entities = [];
		}
		loading = false;
	}

	const filteredEntities = $derived(
		entities.filter((e) => {
			if (!search) return true;
			const q = search.toLowerCase();
			return (
				e.name.toLowerCase().includes(q) ||
				e.entity_type.toLowerCase().includes(q) ||
				(e.description?.toLowerCase().includes(q) ?? false)
			);
		}),
	);

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
		aria-labelledby="entity-picker-title"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 400px; max-height: 500px"
	>
		<h2 id="entity-picker-title" class="text-lg font-bold">Link Existing Entity</h2>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">Search and select an entity to add to the canvas.</p>

		<div class="mt-3">
			<label for="entity-picker-search" class="sr-only">Search entities</label>
			<input
				id="entity-picker-search"
				bind:value={search}
				type="search"
				placeholder="Search entities..."
				autocomplete="off"
				class="w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			/>
		</div>

		<div class="mt-3" style="max-height: 280px; overflow-y: auto">
			{#if loading}
				<p class="text-sm" style="color: var(--color-muted)">Loading entities...</p>
			{:else if filteredEntities.length === 0}
				<p class="text-sm" style="color: var(--color-muted)">No entities found.</p>
			{:else}
				<ul class="flex flex-col gap-1" role="listbox" aria-label="Available entities">
					{#each filteredEntities as entity}
						<li role="option" aria-selected="false">
							<button
								onclick={() => onselect(entity)}
								class="w-full rounded border p-2 text-left text-sm hover:bg-[var(--color-surface)]"
								style="border-color: var(--color-border); color: var(--color-fg)"
							>
								<span class="font-medium">{entity.name}</span>
								<span class="ml-2 rounded px-1.5 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
									{entity.entity_type}
								</span>
								{#if entity.description}
									<p class="mt-0.5 text-xs" style="color: var(--color-muted)">
										{entity.description.slice(0, 80)}{entity.description.length > 80 ? '...' : ''}
									</p>
								{/if}
							</button>
						</li>
					{/each}
				</ul>
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
