<script lang="ts">
	import { apiFetch } from '$lib/utils/api';
	import type { IrisCollection } from '$lib/types/api';

	interface Props {
		value: string;
		onchange: (collectionId: string, collectionName?: string) => void;
		showAll?: boolean;
		label?: string;
	}

	let { value, onchange, showAll = true, label = 'Collection' }: Props = $props();

	let collections = $state<IrisCollection[]>([]);
	let loading = $state(true);

	export async function reload() {
		await loadCollections();
	}

	async function loadCollections() {
		loading = true;
		try {
			const data = await apiFetch<{ items: IrisCollection[] }>('/api/collections');
			collections = data.items;
		} catch {
			collections = [];
		}
		loading = false;
	}

	function handleChange(e: Event) {
		const select = e.target as HTMLSelectElement;
		const selected = collections.find((c) => c.id === select.value);
		onchange(select.value, selected?.name);
	}

	$effect(() => {
		loadCollections();
	});
</script>

<div class="flex items-center gap-2">
	<label for="collection-selector" class="text-sm font-medium" style="color: var(--color-fg)">
		{label}
	</label>
	<select
		id="collection-selector"
		{value}
		onchange={handleChange}
		disabled={loading}
		class="rounded border px-3 py-1.5 text-sm"
		style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
	>
		{#if showAll}
			<option value="">All collections</option>
		{/if}
		{#each collections as c}
			<option value={c.id}>{c.name} ({c.set_count})</option>
		{/each}
	</select>
</div>
