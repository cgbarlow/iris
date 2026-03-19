<script lang="ts">
	import { apiFetch } from '$lib/utils/api';
	import { getActiveSetId, getActiveSetName } from '$lib/stores/activeSet.svelte.js';
	import SetQA from '$lib/components/SetQA.svelte';
	import type { IrisSet } from '$lib/types/api';

	let sets = $state<IrisSet[]>([]);
	let loading = $state(true);

	const activeSetId = $derived(getActiveSetId());
	const activeSetName = $derived(getActiveSetName());
	let selectedSetId = $state('');

	// Use active set if available, otherwise allow selection
	let effectiveSetId = $derived(selectedSetId || activeSetId || '');

	$effect(() => {
		loadSets();
	});

	$effect(() => {
		if (activeSetId && !selectedSetId) {
			selectedSetId = activeSetId;
		}
	});

	async function loadSets() {
		loading = true;
		try {
			const resp = await apiFetch<{ items: IrisSet[] }>('/api/sets');
			sets = resp.items;
			if (!selectedSetId && activeSetId) {
				selectedSetId = activeSetId;
			} else if (!selectedSetId && sets.length > 0) {
				selectedSetId = sets[0].id;
			}
		} catch {
			// ignore
		}
		loading = false;
	}
</script>

<svelte:head>
	<title>Ask AI — Iris</title>
</svelte:head>

<div class="flex flex-col" style="height: calc(100vh - 56px - 48px); overflow: hidden">
	<div class="flex-none">
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Ask AI</h1>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">
			Ask questions about your architecture models. Select a Set to provide context.
		</p>
	</div>

	{#if loading}
		<p class="mt-4 text-sm" style="color: var(--color-muted)">Loading sets...</p>
	{:else if sets.length === 0}
		<p class="mt-4 text-sm" style="color: var(--color-muted)">No sets available. Import or create a set first.</p>
	{:else}
		<div class="mt-4">
			<label class="flex flex-col gap-1 text-sm" style="color: var(--color-fg)">
				Set
				<select
					bind:value={selectedSetId}
					class="rounded border px-3 py-2"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg); max-width: 400px"
				>
					{#each sets as s (s.id)}
						<option value={s.id}>{s.name}</option>
					{/each}
				</select>
			</label>
		</div>

		{#if effectiveSetId}
			<div class="mt-4 flex-1 overflow-hidden">
				{#key effectiveSetId}
					<SetQA setId={effectiveSetId} />
				{/key}
			</div>
		{/if}
	{/if}
</div>
