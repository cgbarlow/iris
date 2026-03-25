<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { apiFetch } from '$lib/utils/api';
	import type { IrisCollection, IrisSet } from '$lib/types/api';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import DOMPurify from 'dompurify';

	let collection = $state<IrisCollection | null>(null);
	let sets = $state<IrisSet[]>([]);
	let loading = $state(true);
	let saving = $state(false);
	let error = $state<string | null>(null);
	let successMsg = $state<string | null>(null);

	let name = $state('');
	let description = $state('');

	let showDeleteDialog = $state(false);
	let deleting = $state(false);

	let collectionId = $derived(page.params.id);

	$effect(() => {
		loadCollection();
	});

	async function loadCollection() {
		loading = true;
		error = null;
		try {
			const [collectionData, setsData] = await Promise.all([
				apiFetch<IrisCollection>(`/api/collections/${collectionId}`),
				apiFetch<{ items: IrisSet[] }>(`/api/sets?collection_id=${collectionId}&page_size=100`),
			]);
			collection = collectionData;
			sets = setsData.items;

			// Initialize form state
			name = collectionData.name;
			description = collectionData.description ?? '';
		} catch {
			error = 'Failed to load collection';
		}
		loading = false;
	}

	async function handleSave() {
		saving = true;
		error = null;
		successMsg = null;
		try {
			const sanitizedName = DOMPurify.sanitize(name.trim());
			const sanitizedDesc = description.trim()
				? DOMPurify.sanitize(description.trim())
				: null;

			await apiFetch<IrisCollection>(`/api/collections/${collectionId}`, {
				method: 'PUT',
				body: JSON.stringify({
					name: sanitizedName,
					description: sanitizedDesc,
				}),
			});

			successMsg = 'Collection saved successfully';
			await loadCollection();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to save collection';
		}
		saving = false;
	}

	async function handleDelete() {
		deleting = true;
		error = null;
		try {
			await apiFetch(`/api/collections/${collectionId}`, { method: 'DELETE' });
			await goto('/collections');
		} catch {
			error = 'Failed to delete collection';
		}
		deleting = false;
		showDeleteDialog = false;
	}
</script>

<svelte:head>
	<title>{collection?.name ?? 'Collection'} — Iris</title>
</svelte:head>

{#if loading}
	<p style="color: var(--color-muted)">Loading collection...</p>
{:else if error && !collection}
	<div role="alert" style="color: var(--color-danger)">{error}</div>
{:else if collection}
	<div class="flex items-center gap-3">
		<a href="/collections" class="text-sm" style="color: var(--color-primary)">Collections</a>
		<span style="color: var(--color-muted)">/</span>
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">{collection.name}</h1>
	</div>

	{#if error}
		<div role="alert" class="mt-3" style="color: var(--color-danger)">{error}</div>
	{/if}
	{#if successMsg}
		<div class="mt-3" style="color: var(--color-primary)" role="status">{successMsg}</div>
	{/if}

	<form
		onsubmit={(e) => { e.preventDefault(); handleSave(); }}
		class="mt-6"
		style="max-width: 600px"
	>
		<!-- Name -->
		<div>
			<label for="collection-edit-name" class="text-sm font-medium" style="color: var(--color-fg)">
				Name <span style="color: var(--color-danger)">*</span>
			</label>
			<input
				id="collection-edit-name"
				bind:value={name}
				type="text"
				required
				maxlength="255"
				class="mt-1 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			/>
		</div>

		<!-- Description -->
		<div class="mt-4">
			<label for="collection-edit-description" class="text-sm font-medium" style="color: var(--color-fg)">
				Description
			</label>
			<textarea
				id="collection-edit-description"
				bind:value={description}
				rows="3"
				class="mt-1 w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			></textarea>
		</div>

		<!-- Save button -->
		<div class="mt-6">
			<button
				type="submit"
				disabled={saving || !name.trim()}
				class="rounded px-4 py-2 text-sm text-white"
				style="background-color: var(--color-primary)"
			>
				{saving ? 'Saving...' : 'Save Changes'}
			</button>
		</div>
	</form>

	<!-- Sets in this collection -->
	<div class="mt-6" style="max-width: 600px">
		<h2 class="text-sm font-bold" style="color: var(--color-fg)">
			Sets in this collection ({sets.length})
		</h2>
		{#if sets.length === 0}
			<p class="mt-2 text-sm" style="color: var(--color-muted)">No sets in this collection yet.</p>
		{:else}
			<div class="mt-2 flex flex-col gap-1">
				{#each sets as s}
					<a
						href="/sets/{s.id}"
						class="flex items-center justify-between rounded border p-2 text-sm transition-colors"
						style="border-color: var(--color-border); color: var(--color-fg); text-decoration: none"
						onmouseenter={(e) => (e.currentTarget.style.backgroundColor = 'var(--color-surface)')}
						onmouseleave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
					>
						<span style="color: var(--color-primary)">{s.name}</span>
						<span class="text-xs" style="color: var(--color-muted)">
							{s.diagram_count} diagram{s.diagram_count !== 1 ? 's' : ''}, {s.element_count} element{s.element_count !== 1 ? 's' : ''}
						</span>
					</a>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Info -->
	<div class="mt-6 text-sm" style="color: var(--color-muted); max-width: 600px">
		<p>{collection.set_count} set{collection.set_count !== 1 ? 's' : ''} in this collection</p>
	</div>

	<!-- Danger zone -->
	<div
		class="mt-8 rounded border p-4"
		style="border-color: var(--color-danger); max-width: 600px"
	>
		<h2 class="text-sm font-bold" style="color: var(--color-danger)">Danger Zone</h2>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">
			Deleting this collection will soft-delete it and unlink its {collection.set_count} set{collection.set_count !== 1 ? 's' : ''}. The sets themselves will not be deleted.
		</p>
		<button
			onclick={() => (showDeleteDialog = true)}
			class="mt-3 rounded px-4 py-2 text-sm text-white"
			style="background-color: var(--color-danger)"
		>
			Delete Collection
		</button>
	</div>

	<ConfirmDialog
		open={showDeleteDialog}
		title="Delete Collection"
		message="Are you sure you want to delete &quot;{collection.name}&quot;? This will unlink {collection.set_count} set{collection.set_count !== 1 ? 's' : ''} from this collection. The sets themselves will not be deleted. This action cannot be undone."
		confirmLabel={deleting ? 'Deleting...' : 'Delete Collection'}
		onconfirm={handleDelete}
		oncancel={() => (showDeleteDialog = false)}
	/>
{/if}
