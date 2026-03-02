<script lang="ts">
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type { Entity, PaginatedResponse, BatchResult } from '$lib/types/api';
	import { SIMPLE_ENTITY_TYPES } from '$lib/types/canvas';
	import EntityDialog from '$lib/canvas/controls/EntityDialog.svelte';
	import type { SimpleEntityType } from '$lib/types/canvas';
	import Pagination from '$lib/components/Pagination.svelte';
	import SetSelector from '$lib/components/SetSelector.svelte';
	import BatchToolbar from '$lib/components/BatchToolbar.svelte';
	import BatchSetDialog from '$lib/components/BatchSetDialog.svelte';
	import BatchTagDialog from '$lib/components/BatchTagDialog.svelte';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';

	let entities = $state<Entity[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let searchQuery = $state('');
	let typeFilter = $state('');
	let tagFilter = $state('');
	let availableTags = $state<string[]>([]);
	let sortField = $state<'name' | 'entity_type' | 'updated_at'>('name');
	let showCreateDialog = $state(false);
	let groupMode = $state<'none' | 'type' | 'tag'>(
		(typeof window !== 'undefined' &&
			(localStorage.getItem('iris-entities-group') as 'none' | 'type' | 'tag')) ||
			'none'
	);

	// Pagination state
	let page = $state(1);
	let pageSize = $state(50);
	let total = $state(0);

	// Set filter state
	let currentSetId = $state('');

	// Batch selection state
	let selectMode = $state(false);
	let selectedIds = $state<Set<string>>(new Set());
	let lastSelectedId = $state<string | null>(null);
	let showBatchSetDialog = $state(false);
	let showBatchTagDialog = $state(false);
	let showBatchDeleteConfirm = $state(false);

	$effect(() => {
		loadEntities();
	});

	$effect(() => {
		if (typeof window !== 'undefined') {
			localStorage.setItem('iris-entities-group', groupMode);
		}
	});

	async function loadEntities() {
		loading = true;
		try {
			const params = new URLSearchParams();
			params.set('page', String(page));
			params.set('page_size', String(pageSize));
			if (currentSetId) params.set('set_id', currentSetId);
			const data = await apiFetch<PaginatedResponse<Entity>>(`/api/entities?${params}`);
			entities = data.items;
			total = data.total;
			loadAvailableTags();
		} catch {
			error = 'Failed to load entities';
		}
		loading = false;
	}

	async function loadAvailableTags() {
		try {
			const params = currentSetId ? `?set_id=${currentSetId}` : '';
			availableTags = await apiFetch<string[]>(`/api/entities/tags/all${params}`);
		} catch {
			availableTags = [];
		}
	}

	async function handleCreate(name: string, entityType: SimpleEntityType, description: string) {
		try {
			const body: Record<string, unknown> = {
				entity_type: entityType,
				name,
				description,
				data: {},
			};
			if (currentSetId) body.set_id = currentSetId;
			await apiFetch<Entity>('/api/entities', {
				method: 'POST',
				body: JSON.stringify(body),
			});
			showCreateDialog = false;
			await loadEntities();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create entity';
		}
	}

	function handleSetChange(setId: string) {
		currentSetId = setId;
		page = 1;
		loadEntities();
	}

	function handlePageChange(newPage: number) {
		page = newPage;
		loadEntities();
	}

	function handlePageSizeChange(newSize: number) {
		pageSize = newSize;
		page = 1;
		loadEntities();
	}

	function handleItemClick(id: string, event: MouseEvent) {
		const next = new Set(selectedIds);
		if (event.shiftKey && lastSelectedId) {
			const ids = filteredEntities.map(e => e.id);
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
			selectedIds = new Set(filteredEntities.map(e => e.id));
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
			await apiFetch<BatchResult>('/api/batch/entities/delete', {
				method: 'POST',
				body: JSON.stringify({ ids: [...selectedIds] }),
			});
			cancelSelection();
			await loadEntities();
		} catch (e) {
			error = e instanceof ApiError ? `Batch delete failed: ${e.message}` : 'Batch delete failed';
		}
	}

	async function handleBatchClone() {
		try {
			await apiFetch<BatchResult>('/api/batch/entities/clone', {
				method: 'POST',
				body: JSON.stringify({ ids: [...selectedIds] }),
			});
			cancelSelection();
			await loadEntities();
		} catch (e) {
			error = e instanceof ApiError ? `Batch clone failed: ${e.message}` : 'Batch clone failed';
		}
	}

	async function handleBatchMoveSet(setId: string) {
		showBatchSetDialog = false;
		try {
			await apiFetch<BatchResult>('/api/batch/entities/set', {
				method: 'POST',
				body: JSON.stringify({ ids: [...selectedIds], set_id: setId }),
			});
			cancelSelection();
			await loadEntities();
		} catch (e) {
			error = e instanceof ApiError ? `Batch move failed: ${e.message}` : 'Batch move failed';
		}
	}

	async function handleBatchTags(addTags: string[], removeTags: string[]) {
		showBatchTagDialog = false;
		try {
			await apiFetch<BatchResult>('/api/batch/entities/tags', {
				method: 'POST',
				body: JSON.stringify({ ids: [...selectedIds], add_tags: addTags, remove_tags: removeTags }),
			});
			cancelSelection();
			await loadEntities();
		} catch (e) {
			error = e instanceof ApiError ? `Batch tag update failed: ${e.message}` : 'Batch tag update failed';
		}
	}

	const filteredEntities = $derived(
		entities
			.filter((e) => {
				if (typeFilter && e.entity_type !== typeFilter) return false;
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
				if (sortField === 'entity_type') return a.entity_type.localeCompare(b.entity_type);
				return (b.updated_at ?? '').localeCompare(a.updated_at ?? '');
			})
	);

	const groupedEntities = $derived.by(() => {
		const items = filteredEntities;
		if (groupMode === 'none') return [{ key: '', items }];

		const groups = new Map<string, Entity[]>();

		if (groupMode === 'type') {
			for (const e of items) {
				const key = e.entity_type;
				if (!groups.has(key)) groups.set(key, []);
				groups.get(key)!.push(e);
			}
		} else if (groupMode === 'tag') {
			const untagged: Entity[] = [];
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
		filteredEntities.length > 0 && filteredEntities.every(e => selectedIds.has(e.id))
	);
</script>

<svelte:head>
	<title>Entities — Iris</title>
</svelte:head>

<div class="flex items-center justify-between">
	<div>
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Entities</h1>
		<p class="mt-2" style="color: var(--color-muted)">Browse and manage architectural entities.</p>
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
			New Entity
		</button>
	</div>
</div>

<!-- Filters -->
<div class="mt-4 flex flex-wrap gap-3">
	<SetSelector value={currentSetId} onchange={handleSetChange} />
	<div>
		<label for="entity-search" class="sr-only">Search entities</label>
		<input
			id="entity-search"
			bind:value={searchQuery}
			type="search"
			placeholder="Search entities..."
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		/>
	</div>
	<div>
		<label for="entity-type-filter" class="sr-only">Filter by type</label>
		<select
			id="entity-type-filter"
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
		<label for="entity-tag-filter" class="sr-only">Filter by tag</label>
		<select
			id="entity-tag-filter"
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
		<label for="entity-sort" class="sr-only">Sort by</label>
		<select
			id="entity-sort"
			bind:value={sortField}
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		>
			<option value="name">Sort by name</option>
			<option value="entity_type">Sort by type</option>
			<option value="updated_at">Sort by updated</option>
		</select>
	</div>
	<div>
		<label for="entity-group" class="sr-only">Group by</label>
		<select
			id="entity-group"
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
		<p style="color: var(--color-muted)">Loading entities...</p>
	{:else if error}
		<div role="alert" style="color: var(--color-danger)">{error}</div>
	{:else if filteredEntities.length === 0}
		<p style="color: var(--color-muted)">No entities found.</p>
	{:else}
		<div class="mb-3 flex items-center gap-3">
			{#if selectMode}
				<label class="flex items-center gap-1.5 text-sm cursor-pointer" style="color: var(--color-fg)">
					<input
						type="checkbox"
						checked={allSelected}
						onclick={toggleSelectAll}
						aria-label="Select all entities"
						class="h-4 w-4"
					/>
					Select all
				</label>
			{/if}
			<p class="text-sm" style="color: var(--color-muted)">
				{filteredEntities.length} entit{filteredEntities.length === 1 ? 'y' : 'ies'}
			</p>
		</div>
		{#each groupedEntities as group}
			{#if group.key}
				<details open class="mt-4">
					<summary class="cursor-pointer text-sm font-medium" style="color: var(--color-fg)">
						{group.key} ({group.items.length})
					</summary>
					<ul class="mt-2 flex flex-col gap-2">
						{#each group.items as entity}
							<li>
								<div class="flex items-center gap-2">
									{#if selectMode}
										<input
											type="checkbox"
											checked={selectedIds.has(entity.id)}
											onclick={(e: MouseEvent) => handleItemClick(entity.id, e)}
											aria-label="Select {entity.name}"
											class="h-4 w-4"
										/>
									{/if}
									<a
										href="/entities/{entity.id}"
										class="flex flex-1 flex-wrap items-center gap-3 rounded border p-3"
										style="border-color: var(--color-border); color: var(--color-fg)"
									>
										<span class="text-sm font-medium" style="color: var(--color-primary)">{entity.name}</span>
										<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">{entity.entity_type}</span>
										{#if entity.set_name}
											<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">{entity.set_name}</span>
										{/if}
										{#if entity.tags && entity.tags.length > 0}
											{#each entity.tags as tag}
												<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-primary); color: white">{tag}</span>
											{/each}
										{/if}
										{#if entity.relationship_count}
											<span class="text-xs" style="color: var(--color-muted)">{entity.relationship_count} rel</span>
										{/if}
										{#if entity.model_usage_count}
											<span class="text-xs" style="color: var(--color-muted)">{entity.model_usage_count} model{entity.model_usage_count === 1 ? '' : 's'}</span>
										{/if}
										{#if entity.description}
											<span class="text-xs" style="color: var(--color-muted)">
												{entity.description.slice(0, 60)}{entity.description.length > 60 ? '...' : ''}
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
					{#each group.items as entity}
						<li>
							<div class="flex items-center gap-2">
								{#if selectMode}
									<input
										type="checkbox"
										checked={selectedIds.has(entity.id)}
										onclick={(e: MouseEvent) => handleItemClick(entity.id, e)}
										aria-label="Select {entity.name}"
										class="h-4 w-4"
									/>
								{/if}
								<a
									href="/entities/{entity.id}"
									class="flex flex-1 flex-wrap items-center gap-3 rounded border p-3"
									style="border-color: var(--color-border); color: var(--color-fg)"
								>
									<span class="text-sm font-medium" style="color: var(--color-primary)">{entity.name}</span>
									<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">{entity.entity_type}</span>
									{#if entity.set_name}
										<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">{entity.set_name}</span>
									{/if}
									{#if entity.tags && entity.tags.length > 0}
										{#each entity.tags as tag}
											<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-primary); color: white">{tag}</span>
										{/each}
									{/if}
									{#if entity.relationship_count}
										<span class="text-xs" style="color: var(--color-muted)">{entity.relationship_count} rel</span>
									{/if}
									{#if entity.model_usage_count}
										<span class="text-xs" style="color: var(--color-muted)">{entity.model_usage_count} model{entity.model_usage_count === 1 ? '' : 's'}</span>
									{/if}
									{#if entity.description}
										<span class="text-xs" style="color: var(--color-muted)">
											{entity.description.slice(0, 60)}{entity.description.length > 60 ? '...' : ''}
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
	title="Delete Selected Entities"
	message="Are you sure you want to delete {selectedIds.size} entit{selectedIds.size !== 1 ? 'ies' : 'y'}? This action can be undone."
	confirmLabel="Delete"
	onconfirm={handleBatchDelete}
	oncancel={() => (showBatchDeleteConfirm = false)}
/>
