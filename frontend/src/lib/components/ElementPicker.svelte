<script lang="ts">
	/**
	 * Searchable element picker dialog for linking existing elements to a canvas.
	 */
	import { apiFetch } from '$lib/utils/api';
	import type { Element, PaginatedResponse } from '$lib/types/api';

	interface Props {
		open: boolean;
		onselect: (element: Element) => void;
		oncancel: () => void;
		title?: string;
		subtitle?: string;
	}

	let { open, onselect, oncancel, title = 'Link Existing Element', subtitle = 'Search and select an element to add to the canvas.' }: Props = $props();

	let elements = $state<Element[]>([]);
	let search = $state('');
	let loading = $state(false);
	let dialogEl: HTMLDialogElement | undefined = $state();

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			search = '';
			dialogEl.showModal();
			loadElements();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	async function loadElements() {
		loading = true;
		try {
			const data = await apiFetch<PaginatedResponse<Element>>('/api/elements');
			elements = data.items.filter((e) => !e.is_deleted);
		} catch {
			elements = [];
		}
		loading = false;
	}

	const filteredElements = $derived(
		elements.filter((e) => {
			if (!search) return true;
			const q = search.toLowerCase();
			return (
				e.name.toLowerCase().includes(q) ||
				e.element_type.toLowerCase().includes(q) ||
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
		aria-labelledby="element-picker-title"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 400px; max-height: 500px"
	>
		<h2 id="element-picker-title" class="text-lg font-bold">{title}</h2>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">{subtitle}</p>

		<div class="mt-3">
			<label for="element-picker-search" class="sr-only">Search elements</label>
			<input
				id="element-picker-search"
				bind:value={search}
				type="search"
				placeholder="Search elements..."
				autocomplete="off"
				class="w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			/>
		</div>

		<div class="mt-3" style="max-height: 280px; overflow-y: auto">
			{#if loading}
				<p class="text-sm" style="color: var(--color-muted)">Loading elements...</p>
			{:else if filteredElements.length === 0}
				<p class="text-sm" style="color: var(--color-muted)">No elements found.</p>
			{:else}
				<ul class="flex flex-col gap-1" role="listbox" aria-label="Available elements">
					{#each filteredElements as element}
						<li role="option" aria-selected="false">
							<button
								onclick={() => onselect(element)}
								class="w-full rounded border p-2 text-left text-sm hover:bg-[var(--color-surface)]"
								style="border-color: var(--color-border); color: var(--color-fg)"
							>
								<span class="font-medium">{element.name}</span>
								<span class="ml-2 rounded px-1.5 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
									{element.element_type}
								</span>
								{#if element.description}
									<p class="mt-0.5 text-xs" style="color: var(--color-muted)">
										{element.description.slice(0, 80)}{element.description.length > 80 ? '...' : ''}
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
