<script lang="ts">
	import { goto } from '$app/navigation';
	import { apiFetch } from '$lib/utils/api';
	import { API_BASE_URL } from '$lib/config.js';
	import { getActiveCollectionId, clearActiveCollection, setActiveCollection } from '$lib/stores/activeCollection.svelte.js';
	import { addAiContextItem, removeAiContextItem, getAiContextItems } from '$lib/stores/aiContext.svelte.js';
	import { recordVisit } from '$lib/stores/visitHistory.svelte.js';
	import type { IrisCollection } from '$lib/types/api';
	import CollectionDialog from '$lib/components/CollectionDialog.svelte';

	let contextItems = $derived(getAiContextItems());
	let contextItemIds = $derived(new Set(contextItems.map((i) => i.id)));

	let collections = $state<IrisCollection[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let searchQuery = $state('');
	let viewMode = $state<'list' | 'gallery'>(
		(typeof localStorage !== 'undefined' && localStorage.getItem('collections-view-mode') as 'list' | 'gallery') || 'list'
	);
	let editMode = $state(false);
	let showCreateDialog = $state(false);

	const activeCollectionIdValue = $derived(getActiveCollectionId());

	let filteredCollections = $derived(
		searchQuery.trim()
			? collections.filter(
					(c) =>
						c.name.toLowerCase().includes(searchQuery.trim().toLowerCase()) ||
						(c.description ?? '').toLowerCase().includes(searchQuery.trim().toLowerCase())
				)
			: collections
	);

	$effect(() => {
		loadCollections();
	});

	$effect(() => {
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem('collections-view-mode', viewMode);
		}
	});

	async function loadCollections() {
		loading = true;
		error = null;
		try {
			const data = await apiFetch<{ items: IrisCollection[] }>('/api/collections');
			collections = data.items;
		} catch {
			error = 'Failed to load collections';
		}
		loading = false;
	}

	function handleCollectionClick(collection: IrisCollection) {
		recordVisit({ id: collection.id, type: 'collection', name: collection.name, description: collection.description ?? undefined, href: `/?collection_id=${collection.id}` });
		if (editMode) {
			goto(`/collections/${collection.id}`);
		} else {
			setActiveCollection(collection.id, collection.name);
			goto(`/?collection_id=${collection.id}`);
		}
	}

	function handleResetFilter() {
		clearActiveCollection();
		goto('/');
	}

	async function handleCreate(name: string, description: string | null) {
		try {
			await apiFetch<IrisCollection>('/api/collections', {
				method: 'POST',
				body: JSON.stringify({ name, description }),
			});
			showCreateDialog = false;
			await loadCollections();
		} catch (e: unknown) {
			const apiErr = e as { status?: number };
			error = apiErr.status === 409 ? 'A collection with this name already exists' : 'Failed to create collection';
		}
	}

	function getImageThumbnailUrl(collection: IrisCollection): string | null {
		// v6.17.6 (issue #205 item 5): mirror the sets-page logic.
		// Backend `has_thumbnail_image` is true when either the legacy
		// thumbnail_image BLOB column has bytes or an entity_images
		// attachment exists; `get_collection_thumbnail` resolves the
		// right bytes in priority order.
		if (collection.has_thumbnail_image) {
			return `${API_BASE_URL}/api/collections/${collection.id}/thumbnail`;
		}
		return null;
	}
</script>

<svelte:head>
	<title>Collections — Iris</title>
</svelte:head>

<div class="flex items-center justify-between">
	<div>
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Collections</h1>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">Group and organise related Sets into Collections.</p>
	</div>
	<div class="flex items-center gap-2">
		{#if activeCollectionIdValue}
			<button
				onclick={handleResetFilter}
				class="rounded border px-3 py-1.5 text-sm"
				style="border-color: var(--color-border); color: var(--color-primary)"
			>
				Reset filter
			</button>
		{/if}
		<button
			onclick={() => (editMode = !editMode)}
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); {editMode
				? 'background: var(--color-primary); color: white'
				: 'color: var(--color-fg)'}"
		>
			Edit Collections
		</button>
		<button
			onclick={() => (showCreateDialog = true)}
			class="rounded px-4 py-2 text-sm text-white"
			style="background-color: var(--color-primary)"
		>
			New Collection
		</button>
	</div>
</div>
<div class="mt-3 flex items-center gap-4">
	<input
		type="search"
		bind:value={searchQuery}
		placeholder="Search collections..."
		class="rounded border px-3 py-1.5 text-sm"
		style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg); max-width: 300px; width: 100%"
	/>
	<div class="flex gap-1">
		<button
			onclick={() => (viewMode = 'list')}
			class="rounded px-2 py-1 text-xs"
			style={viewMode === 'list'
				? 'background-color: var(--color-primary); color: white'
				: 'border: 1px solid var(--color-border); color: var(--color-fg)'}
			aria-label="List view"
		>
			List
		</button>
		<button
			onclick={() => (viewMode = 'gallery')}
			class="rounded px-2 py-1 text-xs"
			style={viewMode === 'gallery'
				? 'background-color: var(--color-primary); color: white'
				: 'border: 1px solid var(--color-border); color: var(--color-fg)'}
			aria-label="Gallery view"
		>
			Gallery
		</button>
	</div>
</div>

{#if loading}
	<p class="mt-4" style="color: var(--color-muted)">Loading collections...</p>
{:else if error}
	<div role="alert" class="mt-4" style="color: var(--color-danger)">{error}</div>
{:else if filteredCollections.length === 0}
	<p class="mt-4" style="color: var(--color-muted)">
		{searchQuery.trim() ? 'No collections match your search.' : 'No collections found.'}
	</p>
{:else if viewMode === 'list'}
	<!-- List view -->
	<div class="mt-4 flex flex-col gap-2">
		{#each filteredCollections as collection}
			<div class="card-wrapper" style="position: relative">
				<button
					onclick={() => handleCollectionClick(collection)}
					class="flex items-center gap-4 rounded border p-3 text-left transition-colors"
					style="border-color: {collection.id === activeCollectionIdValue ? 'var(--color-primary)' : 'var(--color-border)'}; color: var(--color-fg); background: transparent; width: 100%; cursor: pointer; {collection.id === activeCollectionIdValue ? 'border-width: 2px' : ''}"
					onmouseenter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-surface)')}
					onmouseleave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
				>
					<div class="min-w-0 flex-1">
						<div class="font-medium" style="color: var(--color-primary)">{collection.name}</div>
						{#if collection.description}
							<div
								class="mt-0.5 truncate text-sm"
								style="color: var(--color-muted)"
							>
								{collection.description}
							</div>
						{/if}
					</div>
					<div class="flex gap-3 text-xs" style="color: var(--color-muted)">
						<span>{collection.set_count} set{collection.set_count !== 1 ? 's' : ''}</span>
					</div>
					{#if editMode}
						<span class="text-xs" style="color: var(--color-primary)">Edit</span>
					{/if}
				</button>
				<div class="ctx-overlay">
					{#if contextItemIds.has(collection.id)}
						<button
							onclick={() => removeAiContextItem(collection.id)}
							class="added-context-btn rounded border px-2 py-1 text-xs"
							style="border-color: var(--color-primary); background: var(--color-primary); color: white; cursor: pointer; display: flex; align-items: center; gap: 4px"
							title="Remove from AI context"
						>
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="12" height="12" aria-hidden="true"><path d="M248,124a56.11,56.11,0,0,0-32-50.61V72a48,48,0,0,0-88-26.49A48,48,0,0,0,40,72v1.39a56,56,0,0,0,0,101.2V176a48,48,0,0,0,88,26.49A48,48,0,0,0,216,176v-1.41A56.09,56.09,0,0,0,248,124ZM88,208a32,32,0,0,1-31.81-28.56A55.87,55.87,0,0,0,64,180h8a8,8,0,0,0,0-16H64A40,40,0,0,1,50.67,86.27,8,8,0,0,0,56,78.73V72a32,32,0,0,1,64,0v68.26A47.8,47.8,0,0,0,88,128a8,8,0,0,0,0,16,32,32,0,0,1,0,64Zm104-44h-8a8,8,0,0,0,0,16h8a55.87,55.87,0,0,0,7.81-.56A32,32,0,1,1,168,144a8,8,0,0,0,0-16,47.8,47.8,0,0,0-32,12.26V72a32,32,0,0,1,64,0v6.73a8,8,0,0,0,5.33,7.54A40,40,0,0,1,192,164Zm16-52a8,8,0,0,1-8,8h-4a36,36,0,0,1-36-36V80a8,8,0,0,1,16,0v4a20,20,0,0,0,20,20h4A8,8,0,0,1,208,112ZM60,120H56a8,8,0,0,1,0-16h4A20,20,0,0,0,80,84V80a8,8,0,0,1,16,0v4A36,36,0,0,1,60,120Z"/></svg>
							In context
						</button>
					{:else}
						<button
							onclick={() => addAiContextItem({ id: collection.id, result_type: 'collection', name: collection.name, set_id: null, set_name: null })}
							class="add-context-btn rounded border py-1 text-xs"
							style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-primary); cursor: pointer"
							title="Add to Iris AI context"
						>
							<span class="add-context-inner">
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="12" height="12" aria-hidden="true" style="flex-shrink: 0"><path d="M248,124a56.11,56.11,0,0,0-32-50.61V72a48,48,0,0,0-88-26.49A48,48,0,0,0,40,72v1.39a56,56,0,0,0,0,101.2V176a48,48,0,0,0,88,26.49A48,48,0,0,0,216,176v-1.41A56.09,56.09,0,0,0,248,124ZM88,208a32,32,0,0,1-31.81-28.56A55.87,55.87,0,0,0,64,180h8a8,8,0,0,0,0-16H64A40,40,0,0,1,50.67,86.27,8,8,0,0,0,56,78.73V72a32,32,0,0,1,64,0v68.26A47.8,47.8,0,0,0,88,128a8,8,0,0,0,0,16,32,32,0,0,1,0,64Zm104-44h-8a8,8,0,0,0,0,16h8a55.87,55.87,0,0,0,7.81-.56A32,32,0,1,1,168,144a8,8,0,0,0,0-16,47.8,47.8,0,0,0-32,12.26V72a32,32,0,0,1,64,0v6.73a8,8,0,0,0,5.33,7.54A40,40,0,0,1,192,164Zm16-52a8,8,0,0,1-8,8h-4a36,36,0,0,1-36-36V80a8,8,0,0,1,16,0v4a20,20,0,0,0,20,20h4A8,8,0,0,1,208,112ZM60,120H56a8,8,0,0,1,0-16h4A20,20,0,0,0,80,84V80a8,8,0,0,1,16,0v4A36,36,0,0,1,60,120Z"/></svg>
								<span class="add-context-plus">+</span>
								<span class="add-context-label">Add to context</span>
							</span>
						</button>
					{/if}
				</div>
			</div>
		{/each}
	</div>
{:else}
	<!-- Gallery view -->
	<div class="mt-4 grid gap-4" style="grid-template-columns: repeat(auto-fill, minmax(200px, 1fr))">
		{#each filteredCollections as collection}
			{@const imageUrl = getImageThumbnailUrl(collection)}
			<div class="card-wrapper" style="position: relative">
				<button
					onclick={() => handleCollectionClick(collection)}
					class="flex flex-col items-center rounded border p-4 text-center transition-colors"
					style="border-color: {collection.id === activeCollectionIdValue ? 'var(--color-primary)' : 'var(--color-border)'}; color: var(--color-fg); background: transparent; cursor: pointer; width: 100%; {collection.id === activeCollectionIdValue ? 'border-width: 2px' : ''}"
					onmouseenter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-surface)')}
					onmouseleave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
				>
					<div
						class="flex items-center justify-center rounded"
						style="width: 160px; height: 100px; background-color: var(--color-bg); border: 1px solid var(--color-border); overflow: hidden"
					>
						{#if imageUrl}
							<!-- v6.17.6 (issue #205): render the attached image
								 as the gallery tile thumbnail. -->
							<img
								src={imageUrl}
								alt="{collection.name} thumbnail"
								style="max-width: 100%; max-height: 100%; object-fit: contain"
							/>
						{:else}
							<span class="text-2xl" style="color: var(--color-muted)">C</span>
						{/if}
					</div>
					<div class="mt-2 font-medium text-sm" style="color: var(--color-primary)">{collection.name}</div>
					<div class="mt-1 text-xs" style="color: var(--color-muted)">
						{collection.set_count} set{collection.set_count !== 1 ? 's' : ''}
					</div>
					{#if collection.description}
						<div class="mt-1 text-xs" style="color: var(--color-muted); overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical">{collection.description}</div>
					{/if}
					{#if editMode}
						<span class="mt-1 text-xs" style="color: var(--color-primary)">Edit</span>
					{/if}
				</button>
				<div class="ctx-overlay">
					{#if contextItemIds.has(collection.id)}
						<button
							onclick={() => removeAiContextItem(collection.id)}
							class="added-context-btn rounded border px-2 py-1 text-xs"
							style="border-color: var(--color-primary); background: var(--color-primary); color: white; cursor: pointer; display: flex; align-items: center; gap: 4px"
							title="Remove from AI context"
						>
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="12" height="12" aria-hidden="true"><path d="M248,124a56.11,56.11,0,0,0-32-50.61V72a48,48,0,0,0-88-26.49A48,48,0,0,0,40,72v1.39a56,56,0,0,0,0,101.2V176a48,48,0,0,0,88,26.49A48,48,0,0,0,216,176v-1.41A56.09,56.09,0,0,0,248,124ZM88,208a32,32,0,0,1-31.81-28.56A55.87,55.87,0,0,0,64,180h8a8,8,0,0,0,0-16H64A40,40,0,0,1,50.67,86.27,8,8,0,0,0,56,78.73V72a32,32,0,0,1,64,0v68.26A47.8,47.8,0,0,0,88,128a8,8,0,0,0,0,16,32,32,0,0,1,0,64Zm104-44h-8a8,8,0,0,0,0,16h8a55.87,55.87,0,0,0,7.81-.56A32,32,0,1,1,168,144a8,8,0,0,0,0-16,47.8,47.8,0,0,0-32,12.26V72a32,32,0,0,1,64,0v6.73a8,8,0,0,0,5.33,7.54A40,40,0,0,1,192,164Zm16-52a8,8,0,0,1-8,8h-4a36,36,0,0,1-36-36V80a8,8,0,0,1,16,0v4a20,20,0,0,0,20,20h4A8,8,0,0,1,208,112ZM60,120H56a8,8,0,0,1,0-16h4A20,20,0,0,0,80,84V80a8,8,0,0,1,16,0v4A36,36,0,0,1,60,120Z"/></svg>
							In context
						</button>
					{:else}
						<button
							onclick={() => addAiContextItem({ id: collection.id, result_type: 'collection', name: collection.name, set_id: null, set_name: null })}
							class="add-context-btn rounded border py-1 text-xs"
							style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-primary); cursor: pointer"
							title="Add to Iris AI context"
						>
							<span class="add-context-inner">
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="12" height="12" aria-hidden="true" style="flex-shrink: 0"><path d="M248,124a56.11,56.11,0,0,0-32-50.61V72a48,48,0,0,0-88-26.49A48,48,0,0,0,40,72v1.39a56,56,0,0,0,0,101.2V176a48,48,0,0,0,88,26.49A48,48,0,0,0,216,176v-1.41A56.09,56.09,0,0,0,248,124ZM88,208a32,32,0,0,1-31.81-28.56A55.87,55.87,0,0,0,64,180h8a8,8,0,0,0,0-16H64A40,40,0,0,1,50.67,86.27,8,8,0,0,0,56,78.73V72a32,32,0,0,1,64,0v68.26A47.8,47.8,0,0,0,88,128a8,8,0,0,0,0,16,32,32,0,0,1,0,64Zm104-44h-8a8,8,0,0,0,0,16h8a55.87,55.87,0,0,0,7.81-.56A32,32,0,1,1,168,144a8,8,0,0,0,0-16,47.8,47.8,0,0,0-32,12.26V72a32,32,0,0,1,64,0v6.73a8,8,0,0,0,5.33,7.54A40,40,0,0,1,192,164Zm16-52a8,8,0,0,1-8,8h-4a36,36,0,0,1-36-36V80a8,8,0,0,1,16,0v4a20,20,0,0,0,20,20h4A8,8,0,0,1,208,112ZM60,120H56a8,8,0,0,1,0-16h4A20,20,0,0,0,80,84V80a8,8,0,0,1,16,0v4A36,36,0,0,1,60,120Z"/></svg>
								<span class="add-context-plus">+</span>
								<span class="add-context-label">Add to context</span>
							</span>
						</button>
					{/if}
				</div>
			</div>
		{/each}
	</div>
{/if}

<CollectionDialog
	open={showCreateDialog}
	oncreate={handleCreate}
	oncancel={() => (showCreateDialog = false)}
/>

<style>
	.ctx-overlay {
		display: none;
		position: absolute;
		bottom: 8px;
		right: 8px;
		z-index: 1;
	}
	.card-wrapper:hover .ctx-overlay,
	.ctx-overlay:has(.added-context-btn) {
		display: block;
	}
	.add-context-btn {
		overflow: hidden;
		white-space: nowrap;
		width: 40px;
		padding-left: 8px;
		padding-right: 8px;
		transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	}
	.add-context-btn:hover {
		width: 128px;
	}
	.add-context-inner {
		display: flex;
		align-items: center;
		gap: 4px;
	}
	.add-context-btn .add-context-plus {
		display: inline-block;
		width: 8px;
		opacity: 1;
		transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.15s ease;
	}
	.add-context-btn:hover .add-context-plus {
		width: 0;
		opacity: 0;
	}
	.add-context-btn .add-context-label {
		display: inline-block;
		width: 0;
		overflow: hidden;
		opacity: 0;
		transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease 0.1s;
	}
	.add-context-btn:hover .add-context-label {
		width: 80px;
		opacity: 1;
	}
</style>
