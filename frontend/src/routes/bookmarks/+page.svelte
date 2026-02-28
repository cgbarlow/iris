<script lang="ts">
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type { Bookmark, Model } from '$lib/types/api';

	interface BookmarkWithModel {
		bookmark: Bookmark;
		model: Model | null;
	}

	let bookmarks = $state<BookmarkWithModel[]>([]);
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
						const model = await apiFetch<Model>(`/api/models/${b.model_id}`);
						return { bookmark: b, model };
					} catch {
						return { bookmark: b, model: null };
					}
				}),
			);
			bookmarks = resolved;
		} catch {
			error = 'Failed to load bookmarks';
		}
		loading = false;
	}

	async function removeBookmark(modelId: string) {
		try {
			await apiFetch(`/api/models/${modelId}/bookmark`, { method: 'DELETE' });
			bookmarks = bookmarks.filter((b) => b.bookmark.model_id !== modelId);
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
	<p class="mt-2" style="color: var(--color-muted)">Your bookmarked models.</p>
</div>

<div class="mt-4" aria-live="polite">
	{#if loading}
		<p style="color: var(--color-muted)">Loading bookmarks...</p>
	{:else if error}
		<div role="alert" style="color: var(--color-danger)">{error}</div>
	{:else if bookmarks.length === 0}
		<p style="color: var(--color-muted)">No bookmarked models yet. Bookmark a model from its detail page.</p>
	{:else}
		<ul class="flex flex-col gap-2">
			{#each bookmarks as { bookmark, model }}
				<li class="flex items-center gap-3 rounded border p-3" style="border-color: var(--color-border)">
					{#if model}
						<a href="/models/{model.id}" class="flex-1" style="color: var(--color-primary)">
							<span class="font-medium">{model.name}</span>
							<span class="ml-2 rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">{model.model_type}</span>
							{#if model.description}
								<span class="ml-2 text-sm" style="color: var(--color-muted)">{model.description.slice(0, 60)}{model.description.length > 60 ? '...' : ''}</span>
							{/if}
						</a>
						<span class="text-xs" style="color: var(--color-muted)">
							Updated {new Date(model.updated_at).toLocaleDateString()}
						</span>
					{:else}
						<span class="flex-1 text-sm" style="color: var(--color-muted)">
							Model {bookmark.model_id} (unavailable)
						</span>
					{/if}
					<button
						onclick={() => removeBookmark(bookmark.model_id)}
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
