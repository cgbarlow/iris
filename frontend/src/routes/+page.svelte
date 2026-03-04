<script lang="ts">
	import { page } from '$app/state';
	import { apiFetch } from '$lib/utils/api';
	import { setActiveSet, clearActiveSet, getActiveSetId } from '$lib/stores/activeSet.svelte.js';
	import type {
		PaginatedResponse,
		Element,
		Diagram,
		Bookmark,
		SearchResult,
		SearchResponse,
		IrisSet,
	} from '$lib/types/api';

	let elementCount = $state(0);
	let diagramCount = $state(0);
	let setCount = $state(0);
	let activeSet = $state<IrisSet | null>(null);
	let bookmarkedDiagrams = $state<Diagram[]>([]);
	let searchQuery = $state('');
	let searchResults = $state<SearchResult[]>([]);
	let searching = $state(false);
	let loading = $state(true);
	let error = $state<string | null>(null);

	let setId = $derived(page.url.searchParams.get('set_id') || '');

	$effect(() => {
		loadDashboard();
	});

	async function loadDashboard() {
		loading = true;
		error = null;
		try {
			const setFilter = setId ? `&set_id=${setId}` : '';

			const [elementsData, diagramsData, bookmarks, setsData] = await Promise.all([
				apiFetch<PaginatedResponse<Element>>(`/api/elements?page_size=1${setFilter}`),
				apiFetch<PaginatedResponse<Diagram>>(`/api/diagrams?page_size=1${setFilter}`),
				apiFetch<Bookmark[]>('/api/bookmarks'),
				apiFetch<{ items: IrisSet[] }>('/api/sets'),
			]);
			elementCount = elementsData.total;
			diagramCount = diagramsData.total;
			setCount = setsData.items.length;

			// Resolve active set if filtering
			if (setId) {
				activeSet = setsData.items.find((s) => s.id === setId) ?? null;
				if (activeSet) setActiveSet(activeSet.id, activeSet.name);
			} else {
				activeSet = null;
			}

			// Resolve bookmarked diagrams
			const diagramPromises = bookmarks.map((b) =>
				apiFetch<Diagram>(`/api/diagrams/${b.diagram_id}`).catch(() => null)
			);
			const resolved = await Promise.all(diagramPromises);
			bookmarkedDiagrams = resolved.filter((d): d is Diagram => d !== null);
		} catch {
			error = 'Failed to load dashboard data';
		}
		loading = false;
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
			const data = await apiFetch<SearchResponse>(`/api/search?q=${encodeURIComponent(q)}${setFilter}`);
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
<p class="mt-1" style="color: var(--color-muted)">Integrated Repository for Information & Systems</p>

{#if loading}
	<p class="mt-4" style="color: var(--color-muted)">Loading dashboard...</p>
{:else if error}
	<div role="alert" class="mt-4" style="color: var(--color-danger)">{error}</div>
{:else}

	<!-- Stats -->
	<div class="mt-6 grid grid-cols-3 gap-4" style="max-width: 600px">
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
				<a href="/sets" style="color: inherit; text-decoration: none">
					<div class="text-3xl font-bold" style="color: var(--color-primary)">{setCount}</div>
					<div class="mt-1 text-sm" style="color: var(--color-muted)">Sets</div>
				</a>
			{/if}
		</div>
		<a
			href={setId ? `/diagrams?set_id=${setId}` : '/diagrams'}
			class="rounded border p-4 text-center"
			style="border-color: var(--color-border); color: var(--color-fg)"
		>
			<div class="text-3xl font-bold" style="color: var(--color-primary)">{diagramCount}</div>
			<div class="mt-1 text-sm" style="color: var(--color-muted)">
				Diagrams{#if activeSet} (filtered){/if}
			</div>
		</a>
		<a
			href={setId ? `/elements?set_id=${setId}` : '/elements'}
			class="rounded border p-4 text-center"
			style="border-color: var(--color-border); color: var(--color-fg)"
		>
			<div class="text-3xl font-bold" style="color: var(--color-primary)">{elementCount}</div>
			<div class="mt-1 text-sm" style="color: var(--color-muted)">
				Elements{#if activeSet} (filtered){/if}
			</div>
		</a>
	</div>

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
