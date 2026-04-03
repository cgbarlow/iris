<script lang="ts">
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type { Bookmark, Diagram, Package, IrisSet } from '$lib/types/api';
	import CollectionSelector from '$lib/components/CollectionSelector.svelte';
	import SetSelector from '$lib/components/SetSelector.svelte';
	import { getActiveSetId, setActiveSet, clearActiveSet } from '$lib/stores/activeSet.svelte.js';
	import { getActiveCollectionId, setActiveCollection, clearActiveCollection } from '$lib/stores/activeCollection.svelte.js';

	interface ResolvedBookmark {
		bookmark: Bookmark;
		diagram: Diagram | null;
		pkg: Package | null;
	}

	let bookmarks = $state<ResolvedBookmark[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let currentSetId = $state(getActiveSetId());
	let currentCollectionId = $state(getActiveCollectionId());
	let setCollectionMap = $state<Record<string, string>>({});
	let setCollectionNameMap = $state<Record<string, string>>({});

	const filteredBookmarks = $derived.by(() => {
		let result = bookmarks;
		if (currentSetId) {
			result = result.filter(
				({ diagram, pkg }) =>
					diagram?.set_id === currentSetId || pkg?.set_id === currentSetId,
			);
		} else if (currentCollectionId) {
			result = result.filter(({ diagram, pkg }) => {
				const sid = diagram?.set_id ?? pkg?.set_id;
				return sid ? setCollectionMap[sid] === currentCollectionId : false;
			});
		}
		return result;
	});

	const groupedBookmarks = $derived.by(() => {
		const groups: Record<string, ResolvedBookmark[]> = {};
		for (const entry of filteredBookmarks) {
			const sid = entry.diagram?.set_id ?? entry.pkg?.set_id;
			const collectionName = sid ? (setCollectionNameMap[sid] ?? 'Uncategorised') : 'Uncategorised';
			(groups[collectionName] ??= []).push(entry);
		}
		return groups;
	});

	$effect(() => {
		loadBookmarks();
	});

	async function loadBookmarks() {
		loading = true;
		error = null;
		try {
			const [bms, setsResp] = await Promise.all([
				apiFetch<Bookmark[]>('/api/bookmarks'),
				apiFetch<{ items: IrisSet[] }>('/api/sets'),
			]);
			// Build set → collection lookups
			const map: Record<string, string> = {};
			const nameMap: Record<string, string> = {};
			for (const s of setsResp.items) {
				if (s.collection_id) {
					map[s.id] = s.collection_id;
					if (s.collection_name) nameMap[s.id] = s.collection_name;
				}
			}
			setCollectionMap = map;
			setCollectionNameMap = nameMap;

			const resolved = await Promise.all(
				bms.map(async (b) => {
					if (b.diagram_id) {
						try {
							const diagram = await apiFetch<Diagram>(`/api/diagrams/${b.diagram_id}`);
							return { bookmark: b, diagram, pkg: null };
						} catch {
							return { bookmark: b, diagram: null, pkg: null };
						}
					} else if (b.package_id) {
						try {
							const pkg = await apiFetch<Package>(`/api/packages/${b.package_id}`);
							return { bookmark: b, diagram: null, pkg };
						} catch {
							return { bookmark: b, diagram: null, pkg: null };
						}
					}
					return { bookmark: b, diagram: null, pkg: null };
				}),
			);
			bookmarks = resolved;
		} catch {
			error = 'Failed to load bookmarks';
		}
		loading = false;
	}

	async function removeBookmark(bookmark: Bookmark) {
		try {
			if (bookmark.diagram_id) {
				await apiFetch(`/api/diagrams/${bookmark.diagram_id}/bookmark`, { method: 'DELETE' });
			} else if (bookmark.package_id) {
				await apiFetch(`/api/packages/${bookmark.package_id}/bookmark`, { method: 'DELETE' });
			}
			bookmarks = bookmarks.filter((b) => b.bookmark !== bookmark);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to remove bookmark';
		}
	}

	function handleCollectionChange(collectionId: string) {
		if (collectionId) {
			setActiveCollection(collectionId, '');
		} else {
			clearActiveCollection();
		}
		currentCollectionId = collectionId;
		currentSetId = '';
		clearActiveSet();
	}

	function handleSetChange(setId: string, setName?: string) {
		if (setId) {
			setActiveSet(setId, setName ?? '');
		} else {
			clearActiveSet();
		}
		currentSetId = setId;
	}
</script>

<svelte:head>
	<title>Bookmarks — Iris</title>
</svelte:head>

<div class="flex items-center justify-between">
	<div>
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Bookmarks</h1>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">Your bookmarked diagrams and packages.</p>
	</div>
	<div class="flex items-center gap-2">
		<CollectionSelector value={currentCollectionId} onchange={handleCollectionChange} />
		<SetSelector value={currentSetId} onchange={handleSetChange} />
	</div>
</div>

<div class="mt-4" aria-live="polite">
	{#if loading}
		<p style="color: var(--color-muted)">Loading bookmarks...</p>
	{:else if error}
		<div role="alert" style="color: var(--color-danger)">{error}</div>
	{:else if bookmarks.length === 0}
		<p style="color: var(--color-muted)">No bookmarks yet. Bookmark a diagram or package from its detail page.</p>
	{:else if filteredBookmarks.length === 0}
		<p style="color: var(--color-muted)">No bookmarks {currentSetId ? 'in this set' : 'in this collection'}.</p>
	{:else}
		{#each Object.entries(groupedBookmarks) as [collectionName, items]}
			<h3 class="mt-5 mb-2 text-sm font-semibold" style="color: var(--color-muted)">{collectionName}</h3>
			<ul class="flex flex-col gap-2">
				{#each items as { bookmark, diagram, pkg }}
					<li class="flex items-center gap-3 rounded border p-3" style="border-color: var(--color-border)">
						{#if diagram}
							<a href="/diagrams/{diagram.id}" class="flex-1" style="color: inherit">
								<div class="flex flex-wrap items-center gap-2">
									<span class="text-sm font-medium" style="color: var(--color-primary)">{diagram.name}</span>
									<span class="rounded border px-2 py-0.5 text-xs" style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-fg)">
										diagram · {diagram.diagram_type}
									</span>
									{#if diagram.set_name}
										<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
											{diagram.set_name}
										</span>
									{/if}
								</div>
								{#if diagram.description}
									<div class="mt-1 text-xs" style="color: var(--color-muted)">{diagram.description.slice(0, 120)}{diagram.description.length > 120 ? '...' : ''}</div>
								{/if}
							</a>
						{:else if pkg}
							<a href="/packages/{pkg.id}" class="flex-1" style="color: inherit">
								<div class="flex flex-wrap items-center gap-2">
									<span class="text-sm font-medium" style="color: var(--color-primary)">{pkg.name}</span>
									<span class="rounded border px-2 py-0.5 text-xs" style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-fg)">
										package
									</span>
									{#if pkg.set_name}
										<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
											{pkg.set_name}
										</span>
									{/if}
								</div>
								{#if pkg.description}
									<div class="mt-1 text-xs" style="color: var(--color-muted)">{pkg.description.slice(0, 120)}{pkg.description.length > 120 ? '...' : ''}</div>
								{/if}
							</a>
						{:else}
							<span class="flex-1 text-sm" style="color: var(--color-muted)">
								{bookmark.diagram_id ? `Diagram ${bookmark.diagram_id}` : `Package ${bookmark.package_id}`} (unavailable)
							</span>
						{/if}
						<button
							onclick={() => removeBookmark(bookmark)}
							class="rounded px-3 py-1 text-sm"
							style="border: 1px solid var(--color-border); color: var(--color-danger)"
						>
							Remove
						</button>
					</li>
				{/each}
			</ul>
		{/each}
	{/if}
</div>
