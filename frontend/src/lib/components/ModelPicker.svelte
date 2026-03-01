<script lang="ts">
	/**
	 * Searchable model picker dialog for inserting model references into a canvas.
	 */
	import { apiFetch } from '$lib/utils/api';
	import type { Model, PaginatedResponse } from '$lib/types/api';

	interface Props {
		open: boolean;
		onselect: (model: Model) => void;
		oncancel: () => void;
		excludeModelId?: string;
	}

	let { open, onselect, oncancel, excludeModelId }: Props = $props();

	let models = $state<Model[]>([]);
	let search = $state('');
	let loading = $state(false);
	let dialogEl: HTMLDialogElement | undefined = $state();

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			search = '';
			dialogEl.showModal();
			loadModels();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	async function loadModels() {
		loading = true;
		try {
			const data = await apiFetch<PaginatedResponse<Model>>('/api/models');
			models = data.items.filter((m) => !m.is_deleted && m.id !== excludeModelId);
		} catch {
			models = [];
		}
		loading = false;
	}

	const filteredModels = $derived(
		models.filter((m) => {
			if (!search) return true;
			const q = search.toLowerCase();
			return (
				m.name.toLowerCase().includes(q) ||
				m.model_type.toLowerCase().includes(q) ||
				(m.description?.toLowerCase().includes(q) ?? false)
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
		aria-labelledby="model-picker-title"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 400px; max-height: 500px"
	>
		<h2 id="model-picker-title" class="text-lg font-bold">Insert Model</h2>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">Search and select a model to insert as a component.</p>

		<div class="mt-3">
			<label for="model-picker-search" class="sr-only">Search models</label>
			<input
				id="model-picker-search"
				bind:value={search}
				type="search"
				placeholder="Search models..."
				autocomplete="off"
				class="w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			/>
		</div>

		<div class="mt-3" style="max-height: 280px; overflow-y: auto">
			{#if loading}
				<p class="text-sm" style="color: var(--color-muted)">Loading models...</p>
			{:else if filteredModels.length === 0}
				<p class="text-sm" style="color: var(--color-muted)">No models found.</p>
			{:else}
				<ul class="flex flex-col gap-1" role="listbox" aria-label="Available models">
					{#each filteredModels as model}
						<li role="option" aria-selected="false">
							<button
								onclick={() => onselect(model)}
								class="w-full rounded border p-2 text-left text-sm hover:bg-[var(--color-surface)]"
								style="border-color: var(--color-border); color: var(--color-fg)"
							>
								<span class="font-medium">{model.name}</span>
								<span class="ml-2 rounded px-1.5 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
									{model.model_type}
								</span>
								{#if model.tags && model.tags.length > 0}
									{#each model.tags as tag}
										<span class="ml-1 rounded px-1.5 py-0.5 text-xs" style="background: var(--color-primary); color: white">{tag}</span>
									{/each}
								{/if}
								{#if model.description}
									<p class="mt-0.5 text-xs" style="color: var(--color-muted)">
										{model.description.slice(0, 80)}{model.description.length > 80 ? '...' : ''}
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
