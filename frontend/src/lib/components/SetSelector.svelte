<script lang="ts">
	import { apiFetch } from '$lib/utils/api';
	import type { IrisSet } from '$lib/types/api';

	interface Props {
		value: string;
		onchange: (setId: string, setName?: string) => void;
		showAll?: boolean;
		label?: string;
		showNewSet?: boolean;
		onNewSet?: () => void;
		/** v6.17.4 (issue #200): constrain the set list to a single
		 *  collection. When set, the dropdown only shows sets whose
		 *  collection_id matches; empty/undefined = all sets. */
		collectionId?: string | null;
	}

	let { value, onchange, showAll = true, label = 'Set', showNewSet = false, onNewSet, collectionId = null }: Props = $props();

	let sets = $state<IrisSet[]>([]);
	let loading = $state(true);
	let previousValue = $state(value);

	export async function reload() {
		await loadSets();
	}

	async function loadSets() {
		loading = true;
		try {
			const url = collectionId
				? `/api/sets?collection_id=${encodeURIComponent(collectionId)}`
				: '/api/sets';
			const data = await apiFetch<{ items: IrisSet[] }>(url);
			sets = data.items;
		} catch {
			sets = [];
		}
		loading = false;
	}

	function handleChange(e: Event) {
		const select = e.target as HTMLSelectElement;
		if (select.value === '__new__') {
			// Reset to previous value and trigger new set callback
			select.value = previousValue;
			onNewSet?.();
			return;
		}
		previousValue = select.value;
		const selectedSet = sets.find((s) => s.id === select.value);
		onchange(select.value, selectedSet?.name);
	}

	$effect(() => {
		// Read `collectionId` reactively so changing the collection
		// re-fetches the constrained set list (issue #200).
		collectionId;
		loadSets();
	});
</script>

<div class="flex items-center gap-2">
	<label for="set-selector" class="text-sm font-medium" style="color: var(--color-fg)">
		{label}
	</label>
	<select
		id="set-selector"
		{value}
		onchange={handleChange}
		disabled={loading}
		class="rounded border px-3 py-1.5 text-sm"
		style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
	>
		{#if showAll}
			<option value="">All sets</option>
		{/if}
		{#each sets as s}
			<option value={s.id}>{s.name} ({s.diagram_count + s.element_count})</option>
		{/each}
		{#if showNewSet}
			<option value="__new__">+ New Set...</option>
		{/if}
	</select>
</div>
