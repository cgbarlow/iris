<script lang="ts">
	import { apiFetch } from '$lib/utils/api';
	import type { IrisSet } from '$lib/types/api';

	interface Props {
		value: string;
		onchange: (setId: string) => void;
		showAll?: boolean;
		label?: string;
	}

	let { value, onchange, showAll = true, label = 'Set' }: Props = $props();

	let sets = $state<IrisSet[]>([]);
	let loading = $state(true);

	async function loadSets() {
		loading = true;
		try {
			const data = await apiFetch<{ items: IrisSet[] }>('/api/sets');
			sets = data.items;
		} catch {
			sets = [];
		}
		loading = false;
	}

	function handleChange(e: Event) {
		const select = e.target as HTMLSelectElement;
		onchange(select.value);
	}

	$effect(() => {
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
			<option value={s.id}>{s.name} ({s.model_count + s.entity_count})</option>
		{/each}
	</select>
</div>
