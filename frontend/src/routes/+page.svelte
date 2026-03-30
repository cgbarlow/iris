<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import { setActiveSet, clearActiveSet, getActiveSetId } from '$lib/stores/activeSet.svelte.js';
	import { setActiveCollection, clearActiveCollection, getActiveCollectionId } from '$lib/stores/activeCollection.svelte.js';
	import TreeNode from '$lib/components/TreeNode.svelte';
	import DiagramDialog from '$lib/components/DiagramDialog.svelte';
	import type {
		PaginatedResponse,
		Element,
		Diagram,
		Bookmark,
		SearchResult,
		SearchResponse,
		IrisSet,
		IrisCollection,
		DiagramHierarchyNode,
	} from '$lib/types/api';

	let elementCount = $state(0);
	let diagramCount = $state(0);
	let setCount = $state(0);
	let collectionCount = $state(0);
	let activeSet = $state<IrisSet | null>(null);
	let activeCollection = $state<IrisCollection | null>(null);
	let bookmarkedDiagrams = $state<Diagram[]>([]);
	let searchQuery = $state('');
	let searchResults = $state<SearchResult[]>([]);
	let searching = $state(false);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let hierarchyTree = $state<DiagramHierarchyNode[]>([]);
	let hierarchyLoading = $state(false);
	let treeSearchQuery = $state('');
	let treeExpandedIds = $state(new Set<string>());
	let reorderMode = $state(false);
	let showCreateMenu = $state(false);
	let showCreateDiagramDialog = $state(false);
	let showCreatePackageDialog = $state(false);
	let newPackageName = $state('');
	let newPackageDescription = $state('');

	let setId = $derived(page.url.searchParams.get('set_id') || getActiveSetId() || '');
	let collectionId = $derived(page.url.searchParams.get('collection_id') || getActiveCollectionId() || '');

	$effect(() => {
		loadDashboard();
	});

	async function loadDashboard() {
		loading = true;
		error = null;
		try {
			const setFilter = setId ? `&set_id=${setId}` : '';
			const collectionFilter = !setId && collectionId ? `&collection_id=${collectionId}` : '';

			const setsFilter = collectionId ? `?collection_id=${collectionId}` : '';
			const [elementsData, diagramsData, bookmarks, setsData, collectionsData] = await Promise.all([
				apiFetch<PaginatedResponse<Element>>(`/api/elements?page_size=1${setFilter}${collectionFilter}`),
				apiFetch<PaginatedResponse<Diagram>>(`/api/diagrams?page_size=1${setFilter}${collectionFilter}`),
				apiFetch<Bookmark[]>('/api/bookmarks'),
				apiFetch<{ items: IrisSet[] }>(`/api/sets${setsFilter}`),
				apiFetch<{ items: IrisCollection[] }>('/api/collections'),
			]);
			elementCount = elementsData.total;
			diagramCount = diagramsData.total;
			setCount = setsData.items.length;
			collectionCount = collectionsData.items.length;

			// Resolve active set if filtering
			if (setId) {
				activeSet = setsData.items.find((s) => s.id === setId) ?? null;
				if (activeSet && page.url.searchParams.get('set_id')) {
					setActiveSet(activeSet.id, activeSet.name);
				}
			} else {
				activeSet = null;
			}

			// Resolve active collection: from URL param, from active set, or clear
			if (collectionId && !setId) {
				activeCollection = collectionsData.items.find((c) => c.id === collectionId) ?? null;
				if (activeCollection && page.url.searchParams.get('collection_id')) {
					setActiveCollection(activeCollection.id, activeCollection.name);
				}
			} else if (activeSet?.collection_id) {
				activeCollection = collectionsData.items.find((c) => c.id === activeSet!.collection_id) ?? null;
				if (activeCollection) {
					setActiveCollection(activeCollection.id, activeCollection.name);
				}
			} else {
				activeCollection = null;
				clearActiveCollection();
			}

			// Resolve bookmarked diagrams (filter out package bookmarks)
			const diagramPromises = bookmarks
				.filter((b) => b.diagram_id)
				.map((b) =>
					apiFetch<Diagram>(`/api/diagrams/${b.diagram_id}`).catch(() => null)
				);
			const resolved = await Promise.all(diagramPromises);
			bookmarkedDiagrams = resolved.filter((d): d is Diagram => d !== null);
		} catch {
			error = 'Failed to load dashboard data';
		}
		loading = false;

		if (setId) {
			loadHierarchy();
		} else {
			hierarchyTree = [];
		}
	}

	async function loadHierarchy() {
		hierarchyLoading = true;
		try {
			hierarchyTree = await apiFetch<DiagramHierarchyNode[]>(
				`/api/diagrams/hierarchy?set_id=${setId}`
			);
		} catch {
			hierarchyTree = [];
		}
		hierarchyLoading = false;
	}

	async function handleReorder(parentId: string | null, orderedIds: string[]) {
		try {
			await apiFetch('/api/diagrams/reorder', {
				method: 'PUT',
				body: JSON.stringify({
					parent_package_id: parentId,
					ordered_ids: orderedIds,
				}),
			});
			await loadHierarchy();
		} catch {
			// Reload to reset to server state
			await loadHierarchy();
		}
	}

	async function handleCreateDiagram(name: string, diagramType: string, description: string, _tags?: string[], _isTemplate?: boolean, notation?: string) {
		try {
			const body: Record<string, unknown> = { diagram_type: diagramType, name, description, data: {} };
			if (setId) body.set_id = setId;
			if (notation) body.notation = notation;
			const created = await apiFetch<Diagram>('/api/diagrams', {
				method: 'POST',
				body: JSON.stringify(body),
			});
			showCreateDiagramDialog = false;
			await loadHierarchy();
			await goto(`/diagrams/${created.id}`);
		} catch {
			// handled by dialog
		}
	}

	async function handleCreatePackage() {
		if (!newPackageName.trim()) return;
		try {
			const created = await apiFetch<{ id: string }>('/api/packages', {
				method: 'POST',
				body: JSON.stringify({
					name: newPackageName.trim(),
					description: newPackageDescription.trim() || null,
					set_id: setId || undefined,
				}),
			});
			showCreatePackageDialog = false;
			newPackageName = '';
			newPackageDescription = '';
			await loadHierarchy();
			await goto(`/packages/${created.id}`);
		} catch {
			// handled
		}
	}

	async function handleSearch() {
		const q = searchQuery.trim();
		if (!q) {
			searchResults = [];
			return;
		}
		searching = true;
		try {
			const setFilter = setId ? `&set_id=${setId}` : '';
			const collectionFilter = !setId && collectionId ? `&collection_id=${collectionId}` : '';
			const data = await apiFetch<SearchResponse>(`/api/search?q=${encodeURIComponent(q)}${setFilter}${collectionFilter}`);
			searchResults = data.results;
		} catch {
			searchResults = [];
		}
		searching = false;
	}

	let searchTimeout: ReturnType<typeof setTimeout> | undefined;
	function onSearchInput() {
		clearTimeout(searchTimeout);
		searchTimeout = setTimeout(handleSearch, 300);
	}
</script>

<svelte:head>
	<title>Dashboard — Iris</title>
</svelte:head>

<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Dashboard</h1>
<p class="mt-1 text-sm" style="color: var(--color-muted)">Integrated Repository for Information & Systems</p>

{#if loading}
	<p class="mt-4" style="color: var(--color-muted)">Loading dashboard...</p>
{:else if error}
	<div role="alert" class="mt-4" style="color: var(--color-danger)">{error}</div>
{:else}

	<!-- Stats -->
	<div class="mt-6 grid grid-cols-4 gap-4" style="max-width: 800px">
		<div
			class="rounded border p-4 text-center"
			style="border-color: var(--color-border); color: var(--color-fg)"
		>
			{#if activeCollection}
				<div class="text-xl font-bold" style="color: var(--color-fg)">{activeCollection.name}</div>
				<button
					onclick={() => { clearActiveCollection(); clearActiveSet(); window.location.href = '/'; }}
					class="mt-1 inline-block text-sm"
					style="color: var(--color-primary); background: none; border: none; cursor: pointer; padding: 0"
				>
					Reset filter
				</button>
			{:else}
				<a href="/collections" style="color: inherit; text-decoration: none">
					<div class="text-3xl font-bold" style="color: var(--color-primary)">{activeSet && !activeSet.collection_id ? '-' : collectionCount}</div>
					<div class="mt-1 text-sm" style="color: var(--color-muted)">Collections</div>
				</a>
			{/if}
		</div>
		<div
			class="rounded border p-4 text-center"
			style="border-color: var(--color-border); color: var(--color-fg)"
		>
			{#if activeSet}
				<div class="text-xl font-bold" style="color: var(--color-fg)">{activeSet.name}</div>
				<button
					onclick={() => { clearActiveSet(); window.location.href = '/'; }}
					class="mt-1 inline-block text-sm"
					style="color: var(--color-primary); background: none; border: none; cursor: pointer; padding: 0"
				>
					Reset filter
				</button>
			{:else}
				<a href={collectionId ? `/sets?collection_id=${collectionId}` : '/sets'} style="color: inherit; text-decoration: none">
					<div class="text-3xl font-bold" style="color: var(--color-primary)">{setCount}</div>
					<div class="mt-1 text-sm" style="color: var(--color-muted)">Sets{#if activeCollection} (filtered){/if}</div>
				</a>
			{/if}
		</div>
		<a
			href={setId ? `/diagrams?set_id=${setId}` : collectionId ? `/diagrams?collection_id=${collectionId}` : '/diagrams'}
			class="rounded border p-4 text-center"
			style="border-color: var(--color-border); color: var(--color-fg)"
		>
			<div class="text-3xl font-bold" style="color: var(--color-primary)">{diagramCount}</div>
			<div class="mt-1 text-sm" style="color: var(--color-muted)">
				Diagrams{#if activeSet || activeCollection} (filtered){/if}
			</div>
		</a>
		<a
			href={setId ? `/elements?set_id=${setId}` : collectionId ? `/elements?collection_id=${collectionId}` : '/elements'}
			class="rounded border p-4 text-center"
			style="border-color: var(--color-border); color: var(--color-fg)"
		>
			<div class="text-3xl font-bold" style="color: var(--color-primary)">{elementCount}</div>
			<div class="mt-1 text-sm" style="color: var(--color-muted)">
				Elements{#if activeSet || activeCollection} (filtered){/if}
			</div>
		</a>
	</div>

	<p class="mt-4 text-sm" style="color: var(--color-muted)">
		Select a Collection or Set above to filter, or use the search below to find diagrams and elements.
	</p>

	<!-- Diagram Hierarchy (when set selected) -->
	{#if activeSet}
		<div class="mt-6" style="max-width: 500px">
			<div class="flex items-center justify-between">
				<h2 class="text-lg font-semibold" style="color: var(--color-fg)">Diagram Hierarchy</h2>
				<div class="flex items-center gap-1" style="position: relative">
					<button
						onclick={() => { showCreateMenu = !showCreateMenu; }}
						class="rounded px-2 py-1 text-xs"
						style="background: var(--color-primary); color: white"
						title="Create new item"
					>+ New</button>
					{#if showCreateMenu}
						<!-- svelte-ignore a11y_no_static_element_interactions -->
						<div style="position: fixed; inset: 0; z-index: 9" onclick={() => (showCreateMenu = false)}></div>
						<div style="position: absolute; top: 100%; right: 0; z-index: 10; margin-top: 4px; min-width: 120px; border-radius: 6px; border: 1px solid var(--color-border); background: var(--color-surface); box-shadow: 0 4px 12px rgba(0,0,0,0.15); overflow: hidden">
							<button onclick={() => { showCreateDiagramDialog = true; showCreateMenu = false; }} class="block w-full px-3 py-2 text-left text-xs" style="color: var(--color-fg); background: none; border: none; cursor: pointer">Diagram</button>
							<button onclick={() => { showCreatePackageDialog = true; showCreateMenu = false; }} class="block w-full px-3 py-2 text-left text-xs" style="color: var(--color-fg); background: none; border: none; border-top: 1px solid var(--color-border); cursor: pointer">Package</button>
						</div>
					{/if}
					<button
						onclick={() => { reorderMode = !reorderMode; }}
						class="rounded px-2 py-1 text-xs"
						style="border: 1px solid {reorderMode ? 'var(--color-primary)' : 'var(--color-border)'}; background: {reorderMode ? 'var(--color-primary)' : 'transparent'}; color: {reorderMode ? 'white' : 'var(--color-muted)'}"
						title={reorderMode ? 'Exit reorder mode' : 'Reorder diagrams'}
					>
						{reorderMode ? 'Done' : 'Reorder'}
					</button>
				</div>
			</div>
			<input
				id="tree-search"
				bind:value={treeSearchQuery}
				type="search"
				placeholder="Filter diagrams..."
				class="mt-2 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			/>
			{#if hierarchyLoading}
				<p class="mt-2 text-sm" style="color: var(--color-muted)">Loading hierarchy...</p>
			{:else if hierarchyTree.length === 0}
				<p class="mt-2 text-sm" style="color: var(--color-muted)">No diagrams in this set.</p>
			{:else}
				<ul role="tree" class="mt-4" style="list-style: none; padding: 0; margin: 0">
					{#each hierarchyTree as node (node.id)}
						<TreeNode {node} searchQuery={treeSearchQuery} expandedIds={treeExpandedIds} siblings={hierarchyTree} onreorder={reorderMode ? handleReorder : undefined} />
					{/each}
				</ul>
			{/if}
		</div>
	{/if}

	<!-- Search -->
	<div class="mt-6">
		<label for="dashboard-search" class="text-sm font-medium" style="color: var(--color-fg)">Search</label>
		<input
			id="dashboard-search"
			bind:value={searchQuery}
			oninput={onSearchInput}
			type="search"
			placeholder="Search elements and diagrams..."
			class="mt-1 w-full rounded border px-3 py-2 text-sm"
			style="max-width: 500px; border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		/>
	</div>

	{#if searching}
		<p class="mt-2 text-sm" style="color: var(--color-muted)">Searching...</p>
	{:else if searchResults.length > 0}
		<div class="mt-3" aria-live="polite">
			<p class="mb-2 text-sm" style="color: var(--color-muted)">{searchResults.length} result{searchResults.length === 1 ? '' : 's'}</p>
			<ul class="flex flex-col gap-2" style="max-width: 500px">
				{#each searchResults as result}
					<li>
						<a
							href={result.deep_link}
							class="flex items-center gap-3 rounded border p-3"
							style="border-color: var(--color-border); color: var(--color-fg)"
						>
							<span class="text-sm font-medium" style="color: var(--color-primary)">{result.name}</span>
							<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
								{result.result_type} · {result.type_detail}
							</span>
						</a>
					</li>
				{/each}
			</ul>
		</div>
	{:else if searchQuery.trim()}
		<p class="mt-2 text-sm" style="color: var(--color-muted)">No results found.</p>
	{/if}

	<!-- Bookmarked Diagrams -->
	{#if bookmarkedDiagrams.length > 0}
		<div class="mt-6">
			<h2 class="text-lg font-semibold" style="color: var(--color-fg)">Bookmarked Diagrams</h2>
			<ul class="mt-2 flex flex-col gap-2" style="max-width: 500px">
				{#each bookmarkedDiagrams as diagram}
					<li>
						<a
							href="/diagrams/{diagram.id}"
							class="flex items-center gap-3 rounded border p-3"
							style="border-color: var(--color-border); color: var(--color-fg)"
						>
							<span class="text-sm font-medium" style="color: var(--color-primary)">{diagram.name}</span>
							<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
								{diagram.diagram_type}
							</span>
						</a>
					</li>
				{/each}
			</ul>
		</div>
	{/if}

{/if}

<DiagramDialog
	open={showCreateDiagramDialog}
	mode="create"
	onsave={handleCreateDiagram}
	oncancel={() => (showCreateDiagramDialog = false)}
/>

{#if showCreatePackageDialog}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div style="position: fixed; inset: 0; z-index: 50; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.4)" onclick={() => (showCreatePackageDialog = false)}>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="rounded-lg p-6 shadow-lg" style="background: var(--color-surface); min-width: 360px" onclick={(e) => e.stopPropagation()}>
			<h3 class="mb-4 text-lg font-semibold" style="color: var(--color-fg)">Create Package</h3>
			<label class="mb-3 block text-sm" style="color: var(--color-fg)">
				Name
				<input
					bind:value={newPackageName}
					class="mt-1 block w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					placeholder="Package name"
				/>
			</label>
			<label class="mb-4 block text-sm" style="color: var(--color-fg)">
				Description
				<textarea
					bind:value={newPackageDescription}
					class="mt-1 block w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					rows="3"
					placeholder="Optional description"
				></textarea>
			</label>
			<div class="flex justify-end gap-2">
				<button onclick={() => (showCreatePackageDialog = false)} class="rounded border px-3 py-1.5 text-sm" style="border-color: var(--color-border); color: var(--color-fg)">Cancel</button>
				<button onclick={handleCreatePackage} disabled={!newPackageName.trim()} class="rounded px-3 py-1.5 text-sm text-white" style="background-color: var(--color-primary)">Create</button>
			</div>
		</div>
	</div>
{/if}
