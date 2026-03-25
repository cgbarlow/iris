<script lang="ts">
	import { apiFetch } from '$lib/utils/api';
	import { getActiveSetId } from '$lib/stores/activeSet.svelte.js';
	import { getActiveCollectionId } from '$lib/stores/activeCollection.svelte.js';
	import SetQA from '$lib/components/SetQA.svelte';
	import MultiSetSelector from '$lib/components/MultiSetSelector.svelte';
	import type { IrisSet, IrisCollection } from '$lib/types/api';

	let allSets = $state<IrisSet[]>([]);
	let collections = $state<IrisCollection[]>([]);
	let loading = $state(true);

	const activeSetId = $derived(getActiveSetId());
	const activeCollectionId = $derived(getActiveCollectionId());

	let selectedCollectionId = $state('');
	let selectedSetIds = $state<string[]>([]);

	// Filter sets by selected collection
	let displayedSets = $derived(
		selectedCollectionId
			? allSets.filter((s) => s.collection_id === selectedCollectionId)
			: allSets
	);

	// Derive a stable key for SetQA re-render
	let setIdsKey = $derived(selectedSetIds.slice().sort().join(','));

	$effect(() => {
		loadData();
	});

	$effect(() => {
		// Auto-select active set/collection if available
		if (activeCollectionId && !selectedCollectionId) {
			selectedCollectionId = activeCollectionId;
		}
		if (activeSetId && selectedSetIds.length === 0) {
			selectedSetIds = [activeSetId];
		}
	});

	async function loadData() {
		loading = true;
		try {
			const [setsResp, collectionsResp] = await Promise.all([
				apiFetch<{ items: IrisSet[] }>('/api/sets'),
				apiFetch<{ items: IrisCollection[] }>('/api/collections'),
			]);
			allSets = setsResp.items;
			collections = collectionsResp.items;

			// Default selection
			if (selectedSetIds.length === 0) {
				if (activeSetId) {
					selectedSetIds = [activeSetId];
				} else if (allSets.length > 0) {
					selectedSetIds = [allSets[0].id];
				}
			}
		} catch {
			// ignore
		}
		loading = false;
	}

	function handleCollectionChange(e: Event) {
		const select = e.target as HTMLSelectElement;
		selectedCollectionId = select.value;
		// When collection changes, pre-select all sets in the collection
		if (selectedCollectionId) {
			const collectionSets = allSets.filter((s) => s.collection_id === selectedCollectionId);
			selectedSetIds = collectionSets.map((s) => s.id);
		} else {
			// Keep current selection when clearing collection filter
		}
	}
</script>

<svelte:head>
	<title>Ask AI — Iris</title>
</svelte:head>

<div class="flex flex-col" style="height: calc(100vh - 56px - 48px); overflow: hidden">
	<div class="flex-none">
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Ask AI</h1>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">
			Ask questions about your architecture models. Select one or more Sets to provide context.
		</p>
	</div>

	{#if loading}
		<p class="mt-4 text-sm" style="color: var(--color-muted)">Loading...</p>
	{:else if allSets.length === 0}
		<p class="mt-4 text-sm" style="color: var(--color-muted)">No sets available. Import or create a set first.</p>
	{:else}
		<div class="mt-4 flex flex-wrap items-start gap-4" style="max-width: 600px">
			{#if collections.length > 0}
				<div class="flex items-center gap-2">
					<label for="ask-collection" class="text-sm font-medium" style="color: var(--color-fg)">Collection</label>
					<select
						id="ask-collection"
						value={selectedCollectionId}
						onchange={handleCollectionChange}
						class="rounded border px-3 py-1.5 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					>
						<option value="">All collections</option>
						{#each collections as c (c.id)}
							<option value={c.id}>{c.name} ({c.set_count})</option>
						{/each}
					</select>
				</div>
			{/if}
			<div class="flex-1" style="min-width: 250px">
				<MultiSetSelector
					sets={displayedSets}
					selectedIds={selectedSetIds}
					onchange={(ids) => { selectedSetIds = ids; }}
				/>
			</div>
		</div>

		{#if selectedSetIds.length > 0}
			<div class="mt-4 flex-1 overflow-hidden">
				{#key setIdsKey}
					<SetQA setIds={selectedSetIds} collectionId={selectedCollectionId || undefined} />
				{/key}
			</div>
		{:else}
			<p class="mt-4 text-sm" style="color: var(--color-muted)">Select at least one set to start asking questions.</p>
		{/if}
	{/if}
</div>
