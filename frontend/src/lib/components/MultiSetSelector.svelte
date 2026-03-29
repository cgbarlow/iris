<script lang="ts">
	import type { IrisSet } from '$lib/types/api';
	import { apiFetch } from '$lib/utils/api';

	interface Package {
		id: string;
		name: string;
		parent_package_id: string | null;
	}

	interface Props {
		sets: IrisSet[];
		selectedIds: string[];
		onchange: (ids: string[]) => void;
		selectedPackageIds?: string[];
		onpackagechange?: (ids: string[]) => void;
		label?: string;
	}

	let {
		sets,
		selectedIds,
		onchange,
		selectedPackageIds = [],
		onpackagechange,
		label = 'Sets',
	}: Props = $props();

	let open = $state(false);
	let expandedSetIds = $state<Set<string>>(new Set());
	let packagesBySet = $state<Record<string, Package[]>>({});
	let loadingPackages = $state<Set<string>>(new Set());

	let summaryText = $derived.by(() => {
		const setCount =
			selectedIds.length === 0
				? 'Select sets...'
				: selectedIds.length === sets.length && sets.length > 0
					? `All sets (${sets.length})`
					: `${selectedIds.length} of ${sets.length} sets`;
		if (selectedPackageIds.length > 0) {
			return `${setCount}, ${selectedPackageIds.length} package${selectedPackageIds.length !== 1 ? 's' : ''}`;
		}
		return setCount;
	});

	function toggleSet(setId: string) {
		if (selectedIds.includes(setId)) {
			onchange(selectedIds.filter((id) => id !== setId));
			// Remove packages from this set
			if (onpackagechange) {
				const setPackageIds = (packagesBySet[setId] ?? []).map((p) => p.id);
				onpackagechange(selectedPackageIds.filter((id) => !setPackageIds.includes(id)));
			}
		} else {
			onchange([...selectedIds, setId]);
		}
	}

	function selectAll() {
		onchange(sets.map((s) => s.id));
	}

	function deselectAll() {
		onchange([]);
		if (onpackagechange) onpackagechange([]);
	}

	async function toggleExpand(setId: string) {
		if (expandedSetIds.has(setId)) {
			expandedSetIds = new Set([...expandedSetIds].filter((id) => id !== setId));
		} else {
			expandedSetIds = new Set([...expandedSetIds, setId]);
			if (!packagesBySet[setId]) {
				await loadPackages(setId);
			}
		}
	}

	async function loadPackages(setId: string) {
		loadingPackages = new Set([...loadingPackages, setId]);
		try {
			const data = await apiFetch<{ items: Package[] }>(`/api/packages?set_id=${setId}`);
			packagesBySet = { ...packagesBySet, [setId]: data.items };
		} catch {
			packagesBySet = { ...packagesBySet, [setId]: [] };
		}
		loadingPackages = new Set([...loadingPackages].filter((id) => id !== setId));
	}

	function togglePackage(packageId: string) {
		if (!onpackagechange) return;
		if (selectedPackageIds.includes(packageId)) {
			onpackagechange(selectedPackageIds.filter((id) => id !== packageId));
		} else {
			onpackagechange([...selectedPackageIds, packageId]);
		}
	}
</script>

<div style="position: relative">
	<label class="mb-1 block text-sm font-medium" style="color: var(--color-fg)">{label}</label>
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
			style="position: absolute; top: 100%; left: 0; z-index: 10; margin-top: 4px; min-width: 320px; max-height: 400px; background: var(--color-surface); border-color: var(--color-border); overflow: hidden; display: flex; flex-direction: column"
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
			<div style="overflow-y: auto; max-height: 360px">
				{#each sets as s (s.id)}
					<div>
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
							{#if onpackagechange && selectedIds.includes(s.id)}
								<button
									type="button"
									onclick={(e: MouseEvent) => { e.stopPropagation(); e.preventDefault(); toggleExpand(s.id); }}
									class="text-xs px-1"
									style="color: var(--color-muted)"
									title="Show packages"
								>
									{expandedSetIds.has(s.id) ? '\u25B4' : '\u25BE'}
								</button>
							{/if}
						</label>

						{#if expandedSetIds.has(s.id) && selectedIds.includes(s.id)}
							<div class="border-t" style="border-color: var(--color-border); padding-left: 2rem">
								{#if loadingPackages.has(s.id)}
									<div class="px-3 py-1 text-xs" style="color: var(--color-muted)">Loading...</div>
								{:else if (packagesBySet[s.id] ?? []).length === 0}
									<div class="px-3 py-1 text-xs" style="color: var(--color-muted)">No packages</div>
								{:else}
									{#each packagesBySet[s.id] as pkg (pkg.id)}
										<label
											class="flex cursor-pointer items-center gap-2 px-3 py-1.5 text-xs transition-colors"
											style="color: var(--color-fg)"
											onmouseenter={(e) => { e.currentTarget.style.backgroundColor = 'var(--color-bg)'; }}
											onmouseleave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; }}
										>
											<input
												type="checkbox"
												checked={selectedPackageIds.includes(pkg.id)}
												onchange={() => togglePackage(pkg.id)}
												style="accent-color: var(--color-primary)"
											/>
											<span class="flex-1 truncate">{pkg.name}</span>
										</label>
									{/each}
								{/if}
							</div>
						{/if}
					</div>
				{/each}
				{#if sets.length === 0}
					<div class="px-3 py-2 text-xs" style="color: var(--color-muted)">No sets available</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
