<script lang="ts">
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type { Bookmark, Diagram, Package } from '$lib/types/api';
	import SetSelector from '$lib/components/SetSelector.svelte';
	import { getActiveSetId, setActiveSet, clearActiveSet } from '$lib/stores/activeSet.svelte.js';

	interface ResolvedBookmark {
		bookmark: Bookmark;
		diagram: Diagram | null;
		pkg: Package | null;
	}

	let bookmarks = $state<ResolvedBookmark[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let currentSetId = $state(getActiveSetId());

	const filteredBookmarks = $derived(
		currentSetId
			? bookmarks.filter(
					({ diagram, pkg }) =>
						diagram?.set_id === currentSetId || pkg?.set_id === currentSetId,
				)
			: bookmarks,
	);

	$effect(() => {
		loadBookmarks();
	});

	async function loadBookmarks() {
		loading = true;
		error = null;
		try {
			const bms = await apiFetch<Bookmark[]>('/api/bookmarks');
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
		<p class="mt-2" style="color: var(--color-muted)">Your bookmarked diagrams and packages.</p>
	</div>
	<SetSelector value={currentSetId} onchange={handleSetChange} />
</div>

<div class="mt-4" aria-live="polite">
	{#if loading}
		<p style="color: var(--color-muted)">Loading bookmarks...</p>
	{:else if error}
		<div role="alert" style="color: var(--color-danger)">{error}</div>
	{:else if bookmarks.length === 0}
		<p style="color: var(--color-muted)">No bookmarks yet. Bookmark a diagram or package from its detail page.</p>
	{:else if filteredBookmarks.length === 0}
		<p style="color: var(--color-muted)">No bookmarks in this set.</p>
	{:else}
		<ul class="flex flex-col gap-2">
			{#each filteredBookmarks as { bookmark, diagram, pkg }}
				<li class="flex items-center gap-3 rounded border p-3" style="border-color: var(--color-border)">
					{#if diagram}
						<a href="/diagrams/{diagram.id}" class="flex-1" style="color: var(--color-primary)">
							<span class="font-medium">{diagram.name}</span>
							<span class="ml-2 rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">{diagram.diagram_type}</span>
							{#if diagram.description}
								<span class="ml-2 text-sm" style="color: var(--color-muted)">{diagram.description.slice(0, 60)}{diagram.description.length > 60 ? '...' : ''}</span>
							{/if}
						</a>
						<span class="text-xs" style="color: var(--color-muted)">
							Updated {new Date(diagram.updated_at).toLocaleDateString()}
						</span>
					{:else if pkg}
						<a href="/packages/{pkg.id}" class="flex-1" style="color: var(--color-primary)">
							<span class="font-medium">{pkg.name}</span>
							<span class="ml-2 rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">package</span>
							{#if pkg.description}
								<span class="ml-2 text-sm" style="color: var(--color-muted)">{pkg.description.slice(0, 60)}{pkg.description.length > 60 ? '...' : ''}</span>
							{/if}
						</a>
						<span class="text-xs" style="color: var(--color-muted)">
							Updated {new Date(pkg.updated_at).toLocaleDateString()}
						</span>
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
	{/if}
</div>
