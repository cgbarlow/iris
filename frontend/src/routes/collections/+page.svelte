<script lang="ts">
	import { goto } from '$app/navigation';
	import { apiFetch } from '$lib/utils/api';
	import { getActiveCollectionId, clearActiveCollection, setActiveCollection } from '$lib/stores/activeCollection.svelte.js';
	import type { IrisCollection } from '$lib/types/api';
	import CollectionDialog from '$lib/components/CollectionDialog.svelte';

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
		{/each}
	</div>
{:else}
	<!-- Gallery view -->
	<div class="mt-4 grid gap-4" style="grid-template-columns: repeat(auto-fill, minmax(200px, 1fr))">
		{#each filteredCollections as collection}
			<button
				onclick={() => handleCollectionClick(collection)}
				class="flex flex-col items-center rounded border p-4 text-center transition-colors"
				style="border-color: {collection.id === activeCollectionIdValue ? 'var(--color-primary)' : 'var(--color-border)'}; color: var(--color-fg); background: transparent; cursor: pointer; {collection.id === activeCollectionIdValue ? 'border-width: 2px' : ''}"
				onmouseenter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-surface)')}
				onmouseleave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
			>
				<div
					class="flex items-center justify-center rounded"
					style="width: 160px; height: 100px; background-color: var(--color-bg); border: 1px solid var(--color-border); overflow: hidden"
				>
					<span class="text-2xl" style="color: var(--color-muted)">C</span>
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
		{/each}
	</div>
{/if}

<CollectionDialog
	open={showCreateDialog}
	oncreate={handleCreate}
	oncancel={() => (showCreateDialog = false)}
/>
