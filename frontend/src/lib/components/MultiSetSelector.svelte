<script lang="ts">
	import type { IrisSet } from '$lib/types/api';

	interface Props {
		sets: IrisSet[];
		selectedIds: string[];
		onchange: (ids: string[]) => void;
		label?: string;
	}

	let { sets, selectedIds, onchange, label = 'Sets' }: Props = $props();

	let open = $state(false);

	let summaryText = $derived(
		selectedIds.length === 0
			? 'Select sets...'
			: selectedIds.length === sets.length && sets.length > 0
				? `All sets (${sets.length})`
				: `${selectedIds.length} of ${sets.length} sets`
	);

	function toggleSet(setId: string) {
		if (selectedIds.includes(setId)) {
			onchange(selectedIds.filter((id) => id !== setId));
		} else {
			onchange([...selectedIds, setId]);
		}
	}

	function selectAll() {
		onchange(sets.map((s) => s.id));
	}

	function deselectAll() {
		onchange([]);
	}
</script>

<div class="flex items-center gap-2" style="position: relative">
	<label class="text-sm font-medium" style="color: var(--color-fg)">{label}</label>
	<button
		type="button"
		onclick={() => { open = !open; }}
		class="rounded border px-3 py-1.5 text-left text-sm"
		style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg); min-width: 200px"
	>
		{summaryText}
		<span class="float-right" style="color: var(--color-muted)">{open ? '\u25B2' : '\u25BC'}</span>
	</button>

	{#if open}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			style="position: fixed; inset: 0; z-index: 9"
			onclick={() => { open = false; }}
		></div>
		<div
			class="rounded border shadow-lg"
			style="position: absolute; top: 100%; left: 0; z-index: 10; margin-top: 4px; min-width: 280px; max-height: 300px; background: var(--color-surface); border-color: var(--color-border); overflow: hidden; display: flex; flex-direction: column"
		>
			<div class="flex items-center gap-2 border-b px-3 py-2" style="border-color: var(--color-border)">
				<button
					type="button"
					onclick={selectAll}
					class="text-xs"
					style="color: var(--color-primary)"
				>
					Select all
				</button>
				<button
					type="button"
					onclick={deselectAll}
					class="text-xs"
					style="color: var(--color-muted)"
				>
					Clear
				</button>
			</div>
			<div style="overflow-y: auto; max-height: 260px">
				{#each sets as s (s.id)}
					<label
						class="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm transition-colors"
						style="color: var(--color-fg)"
						onmouseenter={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-bg)'; }}
						onmouseleave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; }}
					>
						<input
							type="checkbox"
							checked={selectedIds.includes(s.id)}
							onchange={() => toggleSet(s.id)}
							style="accent-color: var(--color-primary)"
						/>
						<span class="flex-1 truncate">{s.name}</span>
						<span class="text-xs" style="color: var(--color-muted)">
							{s.diagram_count + s.element_count}
						</span>
					</label>
				{/each}
				{#if sets.length === 0}
					<div class="px-3 py-2 text-xs" style="color: var(--color-muted)">No sets available</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
