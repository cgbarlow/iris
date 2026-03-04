<script lang="ts">
	import { apiFetch, ApiError } from '$lib/utils/api';
	import { getActiveSetId, setActiveSet, clearActiveSet } from '$lib/stores/activeSet.svelte.js';
	import type { Element, PaginatedResponse, BatchResult } from '$lib/types/api';
	import { SIMPLE_ENTITY_TYPES } from '$lib/types/canvas';
	import EntityDialog from '$lib/canvas/controls/EntityDialog.svelte';
	import type { SimpleEntityType } from '$lib/types/canvas';
	import Pagination from '$lib/components/Pagination.svelte';
	import SetSelector from '$lib/components/SetSelector.svelte';
	import BatchToolbar from '$lib/components/BatchToolbar.svelte';
	import BatchSetDialog from '$lib/components/BatchSetDialog.svelte';
	import BatchTagDialog from '$lib/components/BatchTagDialog.svelte';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';

	let elements = $state<Element[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let searchQuery = $state('');
	let typeFilter = $state('');
	let tagFilter = $state('');
	let availableTags = $state<string[]>([]);
	let sortField = $state<'name' | 'element_type' | 'updated_at'>('name');
	let showCreateDialog = $state(false);
	let groupMode = $state<'none' | 'type' | 'tag'>(
		(typeof window !== 'undefined' &&
			(localStorage.getItem('iris-elements-group') as 'none' | 'type' | 'tag')) ||
			'none'
	);

	// Pagination state
	let page = $state(1);
	let pageSize = $state(50);
	let total = $state(0);

	// Set filter state — initialise from global store
	let currentSetId = $state(getActiveSetId());

	// Batch selection state
	let selectMode = $state(false);
	let selectedIds = $state<Set<string>>(new Set());
	let lastSelectedId = $state<string | null>(null);
	let showBatchSetDialog = $state(false);
	let showBatchTagDialog = $state(false);
	let showBatchDeleteConfirm = $state(false);

	$effect(() => {
		loadElements();
	});

	$effect(() => {
		if (typeof window !== 'undefined') {
			localStorage.setItem('iris-elements-group', groupMode);
		}
	});

	async function loadElements() {
		loading = true;
		try {
			const params = new URLSearchParams();
			params.set('page', String(page));
			params.set('page_size', String(pageSize));
			if (currentSetId) params.set('set_id', currentSetId);
			const data = await apiFetch<PaginatedResponse<Element>>(`/api/elements?${params}`);
			elements = data.items;
			total = data.total;
			loadAvailableTags();
		} catch {
			error = 'Failed to load elements';
		}
		loading = false;
	}

	async function loadAvailableTags() {
		try {
			const params = currentSetId ? `?set_id=${currentSetId}` : '';
			availableTags = await apiFetch<string[]>(`/api/elements/tags/all${params}`);
		} catch {
			availableTags = [];
		}
	}

	async function handleCreate(name: string, elementType: SimpleEntityType, description: string) {
		try {
			const body: Record<string, unknown> = {
				element_type: elementType,
				name,
				description,
				data: {},
			};
			if (currentSetId) body.set_id = currentSetId;
			await apiFetch<Element>('/api/elements', {
				method: 'POST',
				body: JSON.stringify(body),
			});
			showCreateDialog = false;
			await loadElements();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create element';
		}
	}

	function handleSetChange(newSetId: string, setName?: string) {
		currentSetId = newSetId;
		if (newSetId) {
			setActiveSet(newSetId, setName ?? newSetId);
		} else {
			clearActiveSet();
		}
		page = 1;
		loadElements();
	}

	function handlePageChange(newPage: number) {
		page = newPage;
		loadElements();
	}

	function handlePageSizeChange(newSize: number) {
		pageSize = newSize;
		page = 1;
		loadElements();
	}

	function handleItemClick(id: string, event: MouseEvent) {
		const next = new Set(selectedIds);
		if (event.shiftKey && lastSelectedId) {
			const ids = filteredElements.map(e => e.id);
			const lastIdx = ids.indexOf(lastSelectedId);
			const currentIdx = ids.indexOf(id);
			if (lastIdx !== -1 && currentIdx !== -1) {
				const start = Math.min(lastIdx, currentIdx);
				const end = Math.max(lastIdx, currentIdx);
				for (let i = start; i <= end; i++) {
					next.add(ids[i]);
				}
			}
		} else {
			if (next.has(id)) {
				next.delete(id);
			} else {
				next.add(id);
			}
		}
		lastSelectedId = id;
		selectedIds = next;
	}

	function toggleSelectAll() {
		if (allSelected) {
			selectedIds = new Set();
		} else {
			selectedIds = new Set(filteredElements.map(e => e.id));
		}
	}

	function cancelSelection() {
		selectMode = false;
		selectedIds = new Set();
		lastSelectedId = null;
	}

	async function handleBatchDelete() {
		showBatchDeleteConfirm = false;
		try {
			await apiFetch<BatchResult>('/api/batch/elements/delete', {
				method: 'POST',
				body: JSON.stringify({ ids: [...selectedIds] }),
			});
			cancelSelection();
			await loadElements();
		} catch (e) {
			error = e instanceof ApiError ? `Batch delete failed: ${e.message}` : 'Batch delete failed';
		}
	}

	async function handleBatchClone() {
		try {
			await apiFetch<BatchResult>('/api/batch/elements/clone', {
				method: 'POST',
				body: JSON.stringify({ ids: [...selectedIds] }),
			});
			cancelSelection();
			await loadElements();
		} catch (e) {
			error = e instanceof ApiError ? `Batch clone failed: ${e.message}` : 'Batch clone failed';
		}
	}

	async function handleBatchMoveSet(setId: string) {
		showBatchSetDialog = false;
		try {
			await apiFetch<BatchResult>('/api/batch/elements/set', {
				method: 'POST',
				body: JSON.stringify({ ids: [...selectedIds], set_id: setId }),
			});
			cancelSelection();
			await loadElements();
		} catch (e) {
			error = e instanceof ApiError ? `Batch move failed: ${e.message}` : 'Batch move failed';
		}
	}

	async function handleBatchTags(addTags: string[], removeTags: string[]) {
		showBatchTagDialog = false;
		try {
			await apiFetch<BatchResult>('/api/batch/elements/tags', {
				method: 'POST',
				body: JSON.stringify({ ids: [...selectedIds], add_tags: addTags, remove_tags: removeTags }),
			});
			cancelSelection();
			await loadElements();
		} catch (e) {
			error = e instanceof ApiError ? `Batch tag update failed: ${e.message}` : 'Batch tag update failed';
		}
	}

	const filteredElements = $derived(
		elements
			.filter((e) => {
				if (typeFilter && e.element_type !== typeFilter) return false;
				if (tagFilter && !(e.tags ?? []).includes(tagFilter)) return false;
				if (searchQuery) {
					const q = searchQuery.toLowerCase();
					return (
						e.name.toLowerCase().includes(q) ||
						(e.description?.toLowerCase().includes(q) ?? false)
					);
				}
				return true;
			})
			.sort((a, b) => {
				if (sortField === 'name') return a.name.localeCompare(b.name);
				if (sortField === 'element_type') return a.element_type.localeCompare(b.element_type);
				return (b.updated_at ?? '').localeCompare(a.updated_at ?? '');
			})
	);

	const groupedElements = $derived.by(() => {
		const items = filteredElements;
		if (groupMode === 'none') return [{ key: '', items }];

		const groups = new Map<string, Element[]>();

		if (groupMode === 'type') {
			for (const e of items) {
				const key = e.element_type;
				if (!groups.has(key)) groups.set(key, []);
				groups.get(key)!.push(e);
			}
		} else if (groupMode === 'tag') {
			const untagged: Element[] = [];
			for (const e of items) {
				if (e.tags && e.tags.length > 0) {
					for (const tag of e.tags) {
						if (!groups.has(tag)) groups.set(tag, []);
						groups.get(tag)!.push(e);
					}
				} else {
					untagged.push(e);
				}
			}
			if (untagged.length > 0) groups.set('Untagged', untagged);
		}

		return [...groups.entries()]
			.sort(([a], [b]) => a.localeCompare(b))
			.map(([key, items]) => ({ key, items }));
	});

	const allSelected = $derived(
		filteredElements.length > 0 && filteredElements.every(e => selectedIds.has(e.id))
	);
</script>

<svelte:head>
	<title>Elements — Iris</title>
</svelte:head>

<div class="flex items-center justify-between">
	<div>
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Elements</h1>
		<p class="mt-2" style="color: var(--color-muted)">Browse and manage architectural elements.</p>
	</div>
	<div class="flex items-center gap-2">
		<button
			onclick={() => { selectMode = !selectMode; if (!selectMode) cancelSelection(); }}
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); {selectMode ? 'background: var(--color-primary); color: white' : 'color: var(--color-fg)'}"
		>
			{selectMode ? 'Cancel Select' : 'Select'}
		</button>
		<button
			onclick={() => (showCreateDialog = true)}
			class="rounded px-4 py-2 text-sm text-white"
			style="background-color: var(--color-primary)"
		>
			New Element
		</button>
	</div>
</div>

<!-- Filters -->
<div class="mt-4 flex flex-wrap gap-3">
	<SetSelector value={currentSetId} onchange={handleSetChange} />
	<div>
		<label for="element-search" class="sr-only">Search elements</label>
		<input
			id="element-search"
			bind:value={searchQuery}
			type="search"
			placeholder="Search elements..."
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		/>
	</div>
	<div>
		<label for="element-type-filter" class="sr-only">Filter by type</label>
		<select
			id="element-type-filter"
			bind:value={typeFilter}
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		>
			<option value="">All types</option>
			{#each SIMPLE_ENTITY_TYPES as t}
				<option value={t.key}>{t.label}</option>
			{/each}
		</select>
	</div>
	<div>
		<label for="element-tag-filter" class="sr-only">Filter by tag</label>
		<select
			id="element-tag-filter"
			bind:value={tagFilter}
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		>
			<option value="">All tags</option>
			{#each availableTags as tag}
				<option value={tag}>{tag}</option>
			{/each}
		</select>
	</div>
	<div>
		<label for="element-sort" class="sr-only">Sort by</label>
		<select
			id="element-sort"
			bind:value={sortField}
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		>
			<option value="name">Sort by name</option>
			<option value="element_type">Sort by type</option>
			<option value="updated_at">Sort by updated</option>
		</select>
	</div>
	<div>
		<label for="element-group" class="sr-only">Group by</label>
		<select
			id="element-group"
			bind:value={groupMode}
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		>
			<option value="none">Not grouped</option>
			<option value="type">By type</option>
			<option value="tag">By tag</option>
		</select>
	</div>
</div>

<!-- Results -->
<div class="mt-4" aria-live="polite">
	{#if loading}
		<p style="color: var(--color-muted)">Loading elements...</p>
	{:else if error}
		<div role="alert" style="color: var(--color-danger)">{error}</div>
	{:else if filteredElements.length === 0}
		<p style="color: var(--color-muted)">No elements found.</p>
	{:else}
		<div class="mb-3 flex items-center gap-3">
			{#if selectMode}
				<label class="flex items-center gap-1.5 text-sm cursor-pointer" style="color: var(--color-fg)">
					<input
						type="checkbox"
						checked={allSelected}
						onclick={toggleSelectAll}
						aria-label="Select all elements"
						class="h-4 w-4"
					/>
					Select all
				</label>
			{/if}
			<p class="text-sm" style="color: var(--color-muted)">
				{filteredElements.length} element{filteredElements.length === 1 ? '' : 's'}
			</p>
		</div>
		{#each groupedElements as group}
			{#if group.key}
				<details open class="mt-4">
					<summary class="cursor-pointer text-sm font-medium" style="color: var(--color-fg)">
						{group.key} ({group.items.length})
					</summary>
					<ul class="mt-2 flex flex-col gap-2">
						{#each group.items as element}
							<li>
								<div class="flex items-center gap-2">
									{#if selectMode}
										<input
											type="checkbox"
											checked={selectedIds.has(element.id)}
											onclick={(e: MouseEvent) => handleItemClick(element.id, e)}
											aria-label="Select {element.name}"
											class="h-4 w-4"
										/>
									{/if}
									<a
										href="/elements/{element.id}"
										class="flex flex-1 flex-wrap items-center gap-3 rounded border p-3"
										style="border-color: var(--color-border); color: var(--color-fg)"
									>
										<span class="text-sm font-medium" style="color: var(--color-primary)">{element.name}</span>
										<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">{element.element_type}</span>
										{#if element.set_name}
											<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">{element.set_name}</span>
										{/if}
										{#if element.tags && element.tags.length > 0}
											{#each element.tags as tag}
												<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-primary); color: white">{tag}</span>
											{/each}
										{/if}
										{#if element.relationship_count}
											<span class="text-xs" style="color: var(--color-muted)">{element.relationship_count} rel</span>
										{/if}
										{#if element.diagram_usage_count}
											<span class="text-xs" style="color: var(--color-muted)">{element.diagram_usage_count} diagram{element.diagram_usage_count === 1 ? '' : 's'}</span>
										{/if}
										{#if element.description}
											<span class="text-xs" style="color: var(--color-muted)">
												{element.description.slice(0, 60)}{element.description.length > 60 ? '...' : ''}
											</span>
										{/if}
									</a>
								</div>
							</li>
						{/each}
					</ul>
				</details>
			{:else}
				<ul class="flex flex-col gap-2">
					{#each group.items as element}
						<li>
							<div class="flex items-center gap-2">
								{#if selectMode}
									<input
										type="checkbox"
										checked={selectedIds.has(element.id)}
										onclick={(e: MouseEvent) => handleItemClick(element.id, e)}
										aria-label="Select {element.name}"
										class="h-4 w-4"
									/>
								{/if}
								<a
									href="/elements/{element.id}"
									class="flex flex-1 flex-wrap items-center gap-3 rounded border p-3"
									style="border-color: var(--color-border); color: var(--color-fg)"
								>
									<span class="text-sm font-medium" style="color: var(--color-primary)">{element.name}</span>
									<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">{element.element_type}</span>
									{#if element.set_name}
										<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">{element.set_name}</span>
									{/if}
									{#if element.tags && element.tags.length > 0}
										{#each element.tags as tag}
											<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-primary); color: white">{tag}</span>
										{/each}
									{/if}
									{#if element.relationship_count}
										<span class="text-xs" style="color: var(--color-muted)">{element.relationship_count} rel</span>
									{/if}
									{#if element.diagram_usage_count}
										<span class="text-xs" style="color: var(--color-muted)">{element.diagram_usage_count} diagram{element.diagram_usage_count === 1 ? '' : 's'}</span>
									{/if}
									{#if element.description}
										<span class="text-xs" style="color: var(--color-muted)">
											{element.description.slice(0, 60)}{element.description.length > 60 ? '...' : ''}
										</span>
									{/if}
								</a>
							</div>
						</li>
					{/each}
				</ul>
			{/if}
		{/each}

		<!-- Pagination -->
		<Pagination
			{page}
			{pageSize}
			{total}
			onpagechange={handlePageChange}
			onpagesizechange={handlePageSizeChange}
		/>
	{/if}
</div>

<!-- Batch toolbar -->
{#if selectMode && selectedIds.size > 0}
	<BatchToolbar
		selectedCount={selectedIds.size}
		ondelete={() => (showBatchDeleteConfirm = true)}
		onclone={handleBatchClone}
		onmoveset={() => (showBatchSetDialog = true)}
		ontags={() => (showBatchTagDialog = true)}
		oncancel={cancelSelection}
	/>
{/if}

<!-- Dialogs -->
<EntityDialog
	open={showCreateDialog}
	mode="create"
	onsave={handleCreate}
	oncancel={() => (showCreateDialog = false)}
/>

<BatchSetDialog
	open={showBatchSetDialog}
	onconfirm={handleBatchMoveSet}
	oncancel={() => (showBatchSetDialog = false)}
/>

<BatchTagDialog
	open={showBatchTagDialog}
	onconfirm={handleBatchTags}
	oncancel={() => (showBatchTagDialog = false)}
/>

<ConfirmDialog
	open={showBatchDeleteConfirm}
	title="Delete Selected Elements"
	message="Are you sure you want to delete {selectedIds.size} element{selectedIds.size !== 1 ? 's' : ''}? This action can be undone."
	confirmLabel="Delete"
	onconfirm={handleBatchDelete}
	oncancel={() => (showBatchDeleteConfirm = false)}
/>
