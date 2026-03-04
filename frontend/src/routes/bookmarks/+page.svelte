<script lang="ts">
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type { Bookmark, Diagram } from '$lib/types/api';

	interface BookmarkWithDiagram {
		bookmark: Bookmark;
		diagram: Diagram | null;
	}

	let bookmarks = $state<BookmarkWithDiagram[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

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
					try {
						const diagram = await apiFetch<Diagram>(`/api/diagrams/${b.diagram_id}`);
						return { bookmark: b, diagram };
					} catch {
						return { bookmark: b, diagram: null };
					}
				}),
			);
			bookmarks = resolved;
		} catch {
			error = 'Failed to load bookmarks';
		}
		loading = false;
	}

	async function removeBookmark(diagramId: string) {
		try {
			await apiFetch(`/api/diagrams/${diagramId}/bookmark`, { method: 'DELETE' });
			bookmarks = bookmarks.filter((b) => b.bookmark.diagram_id !== diagramId);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to remove bookmark';
		}
	}
</script>

<svelte:head>
	<title>Bookmarks — Iris</title>
</svelte:head>

<div>
	<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Bookmarks</h1>
	<p class="mt-2" style="color: var(--color-muted)">Your bookmarked diagrams.</p>
</div>

<div class="mt-4" aria-live="polite">
	{#if loading}
		<p style="color: var(--color-muted)">Loading bookmarks...</p>
	{:else if error}
		<div role="alert" style="color: var(--color-danger)">{error}</div>
	{:else if bookmarks.length === 0}
		<p style="color: var(--color-muted)">No bookmarked diagrams yet. Bookmark a diagram from its detail page.</p>
	{:else}
		<ul class="flex flex-col gap-2">
			{#each bookmarks as { bookmark, diagram }}
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
					{:else}
						<span class="flex-1 text-sm" style="color: var(--color-muted)">
							Diagram {bookmark.diagram_id} (unavailable)
						</span>
					{/if}
					<button
						onclick={() => removeBookmark(bookmark.diagram_id)}
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
