<script lang="ts">
	import { goto } from '$app/navigation';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type { Model, PaginatedResponse, ModelHierarchyNode, BatchResult } from '$lib/types/api';
	import ModelDialog from '$lib/components/ModelDialog.svelte';
	import ModelThumbnail from '$lib/components/ModelThumbnail.svelte';
	import TreeNode from '$lib/components/TreeNode.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import SetSelector from '$lib/components/SetSelector.svelte';
	import BatchToolbar from '$lib/components/BatchToolbar.svelte';
	import BatchSetDialog from '$lib/components/BatchSetDialog.svelte';
	import BatchTagDialog from '$lib/components/BatchTagDialog.svelte';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';

	let models = $state<Model[]>([]);
	let hierarchyTree = $state<ModelHierarchyNode[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let searchQuery = $state('');
	let sortField = $state<'name' | 'model_type' | 'updated_at'>('name');
	let typeFilter = $state<string>('');
	let tagFilter = $state('');
	let availableTags = $state<string[]>([]);
	let templateFilter = $state(false);
	let showCreateDialog = $state(false);
	let viewMode = $state<'list' | 'gallery' | 'tree'>(
		(typeof window !== 'undefined' && localStorage.getItem('iris-models-view') as 'list' | 'gallery' | 'tree') || 'list'
	);
	let cardSize = $state<number>(
		(typeof window !== 'undefined' && Number(localStorage.getItem('iris-models-card-size'))) || 250
	);
	let thumbnailMode = $state<'svg' | 'png'>('svg');
	let thumbnailErrors = $state<Set<string>>(new Set());
	let currentTheme = $state<'light' | 'dark' | 'high-contrast'>('dark');

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
		loadModels();
	});

	$effect(() => {
		loadThumbnailMode();
	});

	$effect(() => {
		if (typeof document === 'undefined') return;
		const detectTheme = () => {
			const el = document.documentElement;
			if (el.classList.contains('high-contrast')) {
				currentTheme = 'high-contrast';
			} else if (el.classList.contains('dark')) {
				currentTheme = 'dark';
			} else {
				currentTheme = 'light';
			}
		};
		detectTheme();
		const observer = new MutationObserver(detectTheme);
		observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
		return () => observer.disconnect();
	});

	$effect(() => {
		if (typeof window !== 'undefined') {
			localStorage.setItem('iris-models-view', viewMode);
			localStorage.setItem('iris-models-card-size', String(cardSize));
		}
	});

	let hierarchyLoaded = $state(false);
	$effect(() => {
		if (viewMode === 'tree' && !hierarchyLoaded && !loading) {
			loadHierarchy();
		}
	});

	async function loadModels() {
		loading = true;
		hierarchyLoaded = false;
		try {
			const params = new URLSearchParams();
			params.set('page', String(page));
			params.set('page_size', String(pageSize));
			if (currentSetId) params.set('set_id', currentSetId);
			const data = await apiFetch<PaginatedResponse<Model>>(`/api/models?${params}`);
			models = data.items;
			total = data.total;
			loadAvailableTags();
			if (viewMode === 'tree') {
				await loadHierarchy();
			}
		} catch (e) {
			if (e instanceof ApiError) {
				if (e.status === 429) {
					error = 'The server is busy right now. Please wait a moment and try again.';
				} else if (e.status === 401 || e.status === 403) {
					error = 'You need to log in to view models.';
				} else {
					error = 'Something went wrong loading models. Please try again.';
				}
			} else {
				error = 'Unable to connect to the server. Please check your connection and try again.';
			}
		}
		loading = false;
	}

	async function loadHierarchy() {
		try {
			hierarchyTree = await apiFetch<ModelHierarchyNode[]>('/api/models/hierarchy');
			hierarchyLoaded = true;
		} catch {
			hierarchyTree = [];
		}
	}

	async function loadAvailableTags() {
		try {
			const params = currentSetId ? `?set_id=${currentSetId}` : '';
			availableTags = await apiFetch<string[]>(`/api/entities/tags/all${params}`);
		} catch {
			availableTags = [];
		}
	}

	async function loadThumbnailMode() {
		try {
			const settings = await apiFetch<{key: string; value: string}[]>('/api/settings');
			const mode = settings.find(s => s.key === 'gallery_thumbnail_mode');
			if (mode) thumbnailMode = mode.value as 'svg' | 'png';
		} catch {
			// Settings may not exist yet, default to svg
		}
	}

	async function handleCreate(name: string, modelType: string, description: string) {
		try {
			const body: Record<string, unknown> = {
				model_type: modelType,
				name,
				description,
				data: {},
			};
			if (currentSetId) body.set_id = currentSetId;
			const created = await apiFetch<Model>('/api/models', {
				method: 'POST',
				body: JSON.stringify(body),
			});
			showCreateDialog = false;
			await goto(`/models/${created.id}`);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create model';
		}
	}

	function handleSetChange(setId: string) {
		currentSetId = setId;
		page = 1;
		loadModels();
	}

	function handlePageChange(newPage: number) {
		page = newPage;
		loadModels();
	}

	function handlePageSizeChange(newSize: number) {
		pageSize = newSize;
		page = 1;
		loadModels();
	}

	function handleItemClick(id: string, event: MouseEvent) {
		const next = new Set(selectedIds);
		if (event.shiftKey && lastSelectedId) {
			const ids = filteredModels.map(m => m.id);
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
			selectedIds = new Set(filteredModels.map(m => m.id));
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
			await apiFetch<BatchResult>('/api/batch/models/delete', {
				method: 'POST',
				body: JSON.stringify({ ids: [...selectedIds] }),
			});
			cancelSelection();
			await loadModels();
		} catch (e) {
			error = e instanceof ApiError ? `Batch delete failed: ${e.message}` : 'Batch delete failed';
		}
	}

	async function handleBatchClone() {
		try {
			await apiFetch<BatchResult>('/api/batch/models/clone', {
				method: 'POST',
				body: JSON.stringify({ ids: [...selectedIds] }),
			});
			cancelSelection();
			await loadModels();
		} catch (e) {
			error = e instanceof ApiError ? `Batch clone failed: ${e.message}` : 'Batch clone failed';
		}
	}

	async function handleBatchMoveSet(setId: string) {
		showBatchSetDialog = false;
		try {
			await apiFetch<BatchResult>('/api/batch/models/set', {
				method: 'POST',
				body: JSON.stringify({ ids: [...selectedIds], set_id: setId }),
			});
			cancelSelection();
			await loadModels();
		} catch (e) {
			error = e instanceof ApiError ? `Batch move failed: ${e.message}` : 'Batch move failed';
		}
	}

	async function handleBatchTags(addTags: string[], removeTags: string[]) {
		showBatchTagDialog = false;
		try {
			await apiFetch<BatchResult>('/api/batch/models/tags', {
				method: 'POST',
				body: JSON.stringify({ ids: [...selectedIds], add_tags: addTags, remove_tags: removeTags }),
			});
			cancelSelection();
			await loadModels();
		} catch (e) {
			error = e instanceof ApiError ? `Batch tag update failed: ${e.message}` : 'Batch tag update failed';
		}
	}

	const filteredModels = $derived(
		models
			.filter((m) => {
				if (typeFilter && m.model_type.toLowerCase() !== typeFilter.toLowerCase()) {
					return false;
				}
				if (tagFilter && !(m.tags ?? []).includes(tagFilter)) return false;
			if (templateFilter && !(m.tags ?? []).includes('template')) return false;
				if (searchQuery) {
					const q = searchQuery.toLowerCase();
					return (
						m.name.toLowerCase().includes(q) ||
						(m.description?.toLowerCase().includes(q) ?? false)
					);
				}
				return true;
			})
			.sort((a, b) => {
				if (sortField === 'name') return a.name.localeCompare(b.name);
				if (sortField === 'model_type') return a.model_type.localeCompare(b.model_type);
				return (b.updated_at ?? '').localeCompare(a.updated_at ?? '');
			}),
	);

	const allSelected = $derived(
		filteredModels.length > 0 && filteredModels.every(m => selectedIds.has(m.id))
	);
</script>

<svelte:head>
	<title>Models — Iris</title>
</svelte:head>

<div class="flex items-center justify-between">
	<div>
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Models</h1>
		<p class="mt-2" style="color: var(--color-muted)">Browse and manage architectural models.</p>
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
			New Model
		</button>
	</div>
</div>

<!-- Filters -->
<div class="mt-4 flex flex-wrap gap-3">
	<SetSelector value={currentSetId} onchange={handleSetChange} />
	<div>
		<label for="model-search" class="sr-only">Search models</label>
		<input
			id="model-search"
			bind:value={searchQuery}
			type="search"
			placeholder="Search models..."
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		/>
	</div>
	<div>
		<label for="model-type-filter" class="sr-only">Filter by type</label>
		<select
			id="model-type-filter"
			bind:value={typeFilter}
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		>
			<option value="">All</option>
			<option value="simple">Simple</option>
			<option value="component">Component</option>
			<option value="sequence">Sequence</option>
			<option value="uml">UML</option>
			<option value="archimate">ArchiMate</option>
			<option value="roadmap">Roadmap</option>
		</select>
	</div>
	<div>
		<label for="model-tag-filter" class="sr-only">Filter by tag</label>
		<select
			id="model-tag-filter"
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
		<label for="model-sort" class="sr-only">Sort by</label>
		<select
			id="model-sort"
			bind:value={sortField}
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		>
			<option value="name">Sort by name</option>
			<option value="model_type">Sort by type</option>
			<option value="updated_at">Sort by updated</option>
		</select>
	</div>
	<div class="flex items-center gap-1">
		<button
			onclick={() => (viewMode = 'list')}
			aria-label="List view"
			aria-pressed={viewMode === 'list'}
			class="rounded border px-2 py-2 text-sm"
			style="border-color: var(--color-border); {viewMode === 'list' ? 'background: var(--color-primary); color: white' : 'background: var(--color-bg); color: var(--color-fg)'}"
		>
			&#9776;
		</button>
		<button
			onclick={() => (viewMode = 'gallery')}
			aria-label="Gallery view"
			aria-pressed={viewMode === 'gallery'}
			class="rounded border px-2 py-2 text-sm"
			style="border-color: var(--color-border); {viewMode === 'gallery' ? 'background: var(--color-primary); color: white' : 'background: var(--color-bg); color: var(--color-fg)'}"
		>
			&#9638;
		</button>
		<button
			onclick={() => (viewMode = 'tree')}
			aria-label="Tree view"
			aria-pressed={viewMode === 'tree'}
			class="rounded border px-2 py-2 text-sm"
			style="border-color: var(--color-border); {viewMode === 'tree' ? 'background: var(--color-primary); color: white' : 'background: var(--color-bg); color: var(--color-fg)'}"
		>
			&#8862;
		</button>
	</div>
	<button
		onclick={() => (templateFilter = !templateFilter)}
		aria-label="Show templates only"
		aria-pressed={templateFilter}
		class="rounded border px-3 py-2 text-sm"
		style="border-color: var(--color-border); {templateFilter
			? 'background: var(--color-primary); color: white'
			: 'background: var(--color-bg); color: var(--color-fg)'}"
	>
		Templates
	</button>
	{#if viewMode === 'gallery'}
		<div class="flex items-center gap-2">
			<label for="card-size-slider" class="sr-only">Card size</label>
			<input
				id="card-size-slider"
				type="range"
				min="200"
				max="400"
				step="50"
				bind:value={cardSize}
				aria-label="Card size"
				class="w-24"
			/>
		</div>
	{/if}
</div>

<!-- Results -->
<div class="mt-4" aria-live="polite">
	{#if loading}
		<p style="color: var(--color-muted)">Loading models...</p>
	{:else if error}
		<div role="alert" style="color: var(--color-danger)">
			<p>{error}</p>
			<button
				onclick={() => { error = null; loadModels(); }}
				class="mt-2 rounded border px-3 py-1 text-sm"
				style="border-color: var(--color-border); color: var(--color-fg)"
			>
				Retry
			</button>
		</div>
	{:else if filteredModels.length === 0}
		<p style="color: var(--color-muted)">No models found.</p>
	{:else}
		<div class="mb-3 flex items-center gap-3">
			{#if selectMode}
				<label class="flex items-center gap-1.5 text-sm cursor-pointer" style="color: var(--color-fg)">
					<input
						type="checkbox"
						checked={allSelected}
						onclick={toggleSelectAll}
						aria-label="Select all models"
						class="h-4 w-4"
					/>
					Select all
				</label>
			{/if}
			<p class="text-sm" style="color: var(--color-muted)">
				{filteredModels.length} model{filteredModels.length === 1 ? '' : 's'}
			</p>
		</div>
		{#if viewMode === 'tree'}
			<ul role="tree" aria-label="Model hierarchy" class="tree-view" data-testid="models-tree">
				{#if hierarchyTree.length === 0}
					<li style="color: var(--color-muted); padding: 8px">No models found.</li>
				{:else}
					{#each hierarchyTree as node (node.id)}
						<TreeNode {node} searchQuery={searchQuery} />
					{/each}
				{/if}
			</ul>
		{:else if viewMode === 'list'}
			<ul class="flex flex-col gap-2" data-testid="models-list">
				{#each filteredModels as model}
					<li>
						<div class="flex items-center gap-2">
							{#if selectMode}
								<input
									type="checkbox"
									checked={selectedIds.has(model.id)}
									onclick={(e: MouseEvent) => handleItemClick(model.id, e)}
									aria-label="Select {model.name}"
									class="h-4 w-4"
								/>
							{/if}
							<a
								href="/models/{model.id}"
								class="flex flex-1 items-center gap-3 rounded border p-3"
								style="border-color: var(--color-border); color: var(--color-fg)"
							>
								<span class="text-sm font-medium" style="color: var(--color-primary)">
									{model.name}
								</span>
								<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
									{model.model_type}
								</span>
								{#if model.set_name}
									<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
										{model.set_name}
									</span>
								{/if}
								{#if (model.tags ?? []).includes('template')}
									<span class="rounded px-2 py-0.5 text-xs font-medium" style="background: var(--color-success, #16a34a); color: white">Template</span>
								{/if}
								{#if model.tags && model.tags.length > 0}
									{#each model.tags.filter(t => t !== 'template') as tag}
										<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-primary); color: white">{tag}</span>
									{/each}
								{/if}
								{#if model.description}
									<span class="text-xs" style="color: var(--color-muted)">
										{model.description.slice(0, 60)}{model.description.length > 60 ? '...' : ''}
									</span>
								{/if}
							</a>
						</div>
					</li>
				{/each}
			</ul>
		{:else}
			<div class="grid gap-4" data-testid="models-gallery" style="grid-template-columns: repeat(auto-fill, minmax({cardSize}px, 1fr))">
				{#each filteredModels as model}
					<div class="relative flex flex-col rounded border overflow-hidden" style="border-color: var(--color-border); color: var(--color-fg)">
						{#if selectMode}
							<div class="absolute top-2 left-2 z-10">
								<input
									type="checkbox"
									checked={selectedIds.has(model.id)}
									onclick={(e: MouseEvent) => handleItemClick(model.id, e)}
									aria-label="Select {model.name}"
									class="h-4 w-4"
								/>
							</div>
						{/if}
						<a href="/models/{model.id}" class="flex flex-col">
							<div class="flex h-28 items-center justify-center overflow-hidden" style="border-bottom: 1px solid var(--color-border)">
								{#if thumbnailMode === 'png' && !thumbnailErrors.has(model.id)}
									<img
										src="/api/models/{model.id}/thumbnail?theme={currentTheme}"
										alt="Thumbnail for {model.name}"
										class="h-full w-full object-contain"
										loading="lazy"
										onerror={() => { thumbnailErrors = new Set([...thumbnailErrors, model.id]); }}
									/>
								{:else}
									<ModelThumbnail data={model.data} modelType={model.model_type} />
								{/if}
							</div>
							<div class="flex flex-col gap-2 p-4">
								<span class="font-medium" data-testid="card-name" style="color: var(--color-primary)">{model.name}</span>
								<span class="rounded px-2 py-0.5 text-xs w-fit" data-testid="card-type" style="background: var(--color-surface); color: var(--color-muted)">{model.model_type}</span>
								{#if (model.tags ?? []).includes('template')}
									<span class="rounded px-2 py-0.5 text-xs font-medium w-fit" style="background: var(--color-success, #16a34a); color: white">Template</span>
								{/if}
								{#if model.description}
									<p class="text-sm" style="color: var(--color-muted)">{model.description}</p>
								{/if}
								<span class="text-xs mt-auto" style="color: var(--color-muted)">
									Updated {new Date(model.updated_at).toLocaleDateString()}
								</span>
							</div>
						</a>
					</div>
				{/each}
			</div>
		{/if}

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
<ModelDialog
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
	title="Delete Selected Models"
	message="Are you sure you want to delete {selectedIds.size} model{selectedIds.size !== 1 ? 's' : ''}? This action can be undone."
	confirmLabel="Delete"
	onconfirm={handleBatchDelete}
	oncancel={() => (showBatchDeleteConfirm = false)}
/>
