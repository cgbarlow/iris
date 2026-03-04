<script lang="ts">
	/**
	 * Searchable diagram picker dialog for inserting diagram references into a canvas.
	 */
	import { apiFetch } from '$lib/utils/api';
	import type { Diagram, PaginatedResponse } from '$lib/types/api';

	interface Props {
		open: boolean;
		onselect: (diagram: Diagram) => void;
		oncancel: () => void;
		excludeDiagramId?: string;
		title?: string;
	}

	let { open, onselect, oncancel, excludeDiagramId, title = 'Insert Diagram' }: Props = $props();

	let diagrams = $state<Diagram[]>([]);
	let search = $state('');
	let loading = $state(false);
	let dialogEl: HTMLDialogElement | undefined = $state();

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			search = '';
			dialogEl.showModal();
			loadDiagrams();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	async function loadDiagrams() {
		loading = true;
		try {
			const data = await apiFetch<PaginatedResponse<Diagram>>('/api/diagrams');
			diagrams = data.items.filter((m) => !m.is_deleted && m.id !== excludeDiagramId);
		} catch {
			diagrams = [];
		}
		loading = false;
	}

	const filteredDiagrams = $derived(
		diagrams.filter((m) => {
			if (!search) return true;
			const q = search.toLowerCase();
			return (
				m.name.toLowerCase().includes(q) ||
				m.diagram_type.toLowerCase().includes(q) ||
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
		aria-labelledby="diagram-picker-title"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 400px; max-height: 500px"
	>
		<h2 id="diagram-picker-title" class="text-lg font-bold">{title}</h2>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">Search and select a diagram to insert as a component.</p>

		<div class="mt-3">
			<label for="diagram-picker-search" class="sr-only">Search diagrams</label>
			<input
				id="diagram-picker-search"
				bind:value={search}
				type="search"
				placeholder="Search diagrams..."
				autocomplete="off"
				class="w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			/>
		</div>

		<div class="mt-3" style="max-height: 280px; overflow-y: auto">
			{#if loading}
				<p class="text-sm" style="color: var(--color-muted)">Loading diagrams...</p>
			{:else if filteredDiagrams.length === 0}
				<p class="text-sm" style="color: var(--color-muted)">No diagrams found.</p>
			{:else}
				<ul class="flex flex-col gap-1" role="listbox" aria-label="Available diagrams">
					{#each filteredDiagrams as diagram}
						<li role="option" aria-selected="false">
							<button
								onclick={() => onselect(diagram)}
								class="w-full rounded border p-2 text-left text-sm hover:bg-[var(--color-surface)]"
								style="border-color: var(--color-border); color: var(--color-fg)"
							>
								<span class="font-medium">{diagram.name}</span>
								<span class="ml-2 rounded px-1.5 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
									{diagram.diagram_type}
								</span>
								{#if diagram.tags && diagram.tags.length > 0}
									{#each diagram.tags as tag}
										<span class="ml-1 rounded px-1.5 py-0.5 text-xs" style="background: var(--color-primary); color: white">{tag}</span>
									{/each}
								{/if}
								{#if diagram.description}
									<p class="mt-0.5 text-xs" style="color: var(--color-muted)">
										{diagram.description.slice(0, 80)}{diagram.description.length > 80 ? '...' : ''}
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
