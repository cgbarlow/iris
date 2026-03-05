<script lang="ts">
	import { goto } from '$app/navigation';
	import { apiFetch } from '$lib/utils/api';
	import { getActiveSetId, clearActiveSet, setActiveSet } from '$lib/stores/activeSet.svelte.js';
	import type { IrisSet } from '$lib/types/api';
	import SetDialog from '$lib/components/SetDialog.svelte';
	import DiagramThumbnail from '$lib/components/DiagramThumbnail.svelte';

	let sets = $state<IrisSet[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let searchQuery = $state('');
	let viewMode = $state<'list' | 'gallery'>(
		(typeof localStorage !== 'undefined' && localStorage.getItem('sets-view-mode') as 'list' | 'gallery') || 'list'
	);
	let editMode = $state(false);
	let showCreateDialog = $state(false);

	const activeSetIdValue = $derived(getActiveSetId());

	let filteredSets = $derived(
		searchQuery.trim()
			? sets.filter(
					(s) =>
						s.name.toLowerCase().includes(searchQuery.trim().toLowerCase()) ||
						(s.description ?? '').toLowerCase().includes(searchQuery.trim().toLowerCase())
				)
			: sets
	);

	$effect(() => {
		loadSets();
	});

	$effect(() => {
		if (typeof localStorage !== 'undefined') {
			localStorage.setItem('sets-view-mode', viewMode);
		}
	});

	async function loadSets() {
		loading = true;
		error = null;
		try {
			const data = await apiFetch<{ items: IrisSet[] }>('/api/sets');
			sets = data.items;
		} catch {
			error = 'Failed to load sets';
		}
		loading = false;
	}

	function handleSetClick(set: IrisSet) {
		if (editMode) {
			goto(`/sets/${set.id}`);
		} else {
			setActiveSet(set.id, set.name);
			goto(`/?set_id=${set.id}`);
		}
	}

	function handleResetFilter() {
		clearActiveSet();
		goto('/');
	}

	async function handleCreate(name: string, description: string | null) {
		try {
			await apiFetch<IrisSet>('/api/sets', {
				method: 'POST',
				body: JSON.stringify({ name, description }),
			});
			showCreateDialog = false;
			await loadSets();
		} catch {
			error = 'Failed to create set';
		}
	}

	function getImageThumbnailUrl(set: IrisSet): string | null {
		if (set.thumbnail_source === 'image' && set.has_thumbnail_image) {
			return `/api/sets/${set.id}/thumbnail`;
		}
		return null;
	}
</script>

<svelte:head>
	<title>Sets — Iris</title>
</svelte:head>

<div class="flex items-center justify-between">
	<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Sets</h1>
	<div class="flex items-center gap-2">
		{#if activeSetIdValue}
			<button
				onclick={handleResetFilter}
				class="rounded border px-3 py-2 text-sm"
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
			Edit Sets
		</button>
		<button
			onclick={() => (showCreateDialog = true)}
			class="rounded px-4 py-2 text-sm text-white"
			style="background-color: var(--color-primary)"
		>
			New Set
		</button>
	</div>
</div>

<!-- Controls row -->
<div class="mt-4 flex items-center gap-4">
	<input
		type="search"
		bind:value={searchQuery}
		placeholder="Search sets..."
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
	<p class="mt-4" style="color: var(--color-muted)">Loading sets...</p>
{:else if error}
	<div role="alert" class="mt-4" style="color: var(--color-danger)">{error}</div>
{:else if filteredSets.length === 0}
	<p class="mt-4" style="color: var(--color-muted)">
		{searchQuery.trim() ? 'No sets match your search.' : 'No sets found.'}
	</p>
{:else if viewMode === 'list'}
	<!-- List view -->
	<div class="mt-4 flex flex-col gap-2">
		{#each filteredSets as set}
			<button
				onclick={() => handleSetClick(set)}
				class="flex items-center gap-4 rounded border p-3 text-left transition-colors"
				style="border-color: {set.id === activeSetIdValue ? 'var(--color-primary)' : 'var(--color-border)'}; color: var(--color-fg); background: transparent; width: 100%; cursor: pointer; {set.id === activeSetIdValue ? 'border-width: 2px' : ''}"
				onmouseenter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-surface)')}
				onmouseleave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
			>
				<div class="min-w-0 flex-1">
					<div class="font-medium" style="color: var(--color-primary)">{set.name}</div>
					{#if set.description}
						<div
							class="mt-0.5 truncate text-sm"
							style="color: var(--color-muted)"
						>
							{set.description}
						</div>
					{/if}
				</div>
				<div class="flex gap-3 text-xs" style="color: var(--color-muted)">
					<span>{set.diagram_count} diagram{set.diagram_count !== 1 ? 's' : ''}</span>
					<span>{set.element_count} element{set.element_count !== 1 ? 's' : ''}</span>
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
		{#each filteredSets as set}
			{@const imageUrl = getImageThumbnailUrl(set)}
			<button
				onclick={() => handleSetClick(set)}
				class="flex flex-col items-center rounded border p-4 text-center transition-colors"
				style="border-color: {set.id === activeSetIdValue ? 'var(--color-primary)' : 'var(--color-border)'}; color: var(--color-fg); background: transparent; cursor: pointer; {set.id === activeSetIdValue ? 'border-width: 2px' : ''}"
				onmouseenter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-surface)')}
				onmouseleave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
			>
				<div
					class="flex items-center justify-center rounded"
					style="width: 160px; height: 100px; background-color: var(--color-bg); border: 1px solid var(--color-border); overflow: hidden"
				>
					{#if set.thumbnail_diagram_data && set.thumbnail_diagram_type}
						<DiagramThumbnail data={set.thumbnail_diagram_data} diagramType={set.thumbnail_diagram_type} />
					{:else if imageUrl}
						<img
							src={imageUrl}
							alt="{set.name} thumbnail"
							style="max-width: 100%; max-height: 100%; object-fit: contain"
						/>
					{:else}
						<span class="text-2xl" style="color: var(--color-muted)">S</span>
					{/if}
				</div>
				<div class="mt-2 font-medium text-sm" style="color: var(--color-primary)">{set.name}</div>
				<div class="mt-1 text-xs" style="color: var(--color-muted)">
					{set.diagram_count} diagram{set.diagram_count !== 1 ? 's' : ''}, {set.element_count} element{set.element_count !== 1 ? 's' : ''}
				</div>
				{#if set.description}
					<div class="mt-1 text-xs" style="color: var(--color-muted); overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical">{set.description}</div>
				{/if}
				{#if editMode}
					<span class="mt-1 text-xs" style="color: var(--color-primary)">Edit</span>
				{/if}
			</button>
		{/each}
	</div>
{/if}

<SetDialog
	open={showCreateDialog}
	oncreate={handleCreate}
	oncancel={() => (showCreateDialog = false)}
/>
