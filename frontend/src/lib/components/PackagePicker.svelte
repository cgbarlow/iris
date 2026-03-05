<script lang="ts">
	/**
	 * Searchable package picker dialog for selecting a parent package.
	 */
	import { apiFetch } from '$lib/utils/api';
	import type { Package, PaginatedResponse } from '$lib/types/api';

	interface Props {
		open: boolean;
		onselect: (pkg: Package) => void;
		oncancel: () => void;
		excludePackageId?: string;
		title?: string;
		subtitle?: string;
	}

	let {
		open,
		onselect,
		oncancel,
		excludePackageId,
		title = 'Select Package',
		subtitle = 'Search and select a package.',
	}: Props = $props();

	let packages = $state<Package[]>([]);
	let search = $state('');
	let loading = $state(false);
	let dialogEl: HTMLDialogElement | undefined = $state();

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			search = '';
			dialogEl.showModal();
			loadPackages();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	async function loadPackages() {
		loading = true;
		try {
			const data = await apiFetch<PaginatedResponse<Package>>('/api/packages');
			packages = data.items.filter((p) => !p.is_deleted && p.id !== excludePackageId);
		} catch {
			packages = [];
		}
		loading = false;
	}

	const filteredPackages = $derived(
		packages.filter((p) => {
			if (!search) return true;
			const q = search.toLowerCase();
			return (
				p.name.toLowerCase().includes(q) ||
				(p.description?.toLowerCase().includes(q) ?? false)
			);
		}),
	);

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			oncancel();
		}
	}
</script>

{#if open}
	<dialog
		bind:this={dialogEl}
		onkeydown={handleKeydown}
		aria-labelledby="package-picker-title"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 400px; max-height: 500px"
	>
		<h2 id="package-picker-title" class="text-lg font-bold">{title}</h2>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">{subtitle}</p>

		<div class="mt-3">
			<label for="package-picker-search" class="sr-only">Search packages</label>
			<input
				id="package-picker-search"
				bind:value={search}
				type="search"
				placeholder="Search packages..."
				autocomplete="off"
				class="w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			/>
		</div>

		<div class="mt-3" style="max-height: 280px; overflow-y: auto">
			{#if loading}
				<p class="text-sm" style="color: var(--color-muted)">Loading packages...</p>
			{:else if filteredPackages.length === 0}
				<p class="text-sm" style="color: var(--color-muted)">No packages found.</p>
			{:else}
				<ul class="flex flex-col gap-1" role="listbox" aria-label="Available packages">
					{#each filteredPackages as pkg}
						<li role="option" aria-selected="false">
							<button
								onclick={() => onselect(pkg)}
								class="w-full rounded border p-2 text-left text-sm hover:bg-[var(--color-surface)]"
								style="border-color: var(--color-border); color: var(--color-fg)"
							>
								<span class="font-medium">{pkg.name}</span>
								{#if pkg.description}
									<p class="mt-0.5 text-xs" style="color: var(--color-muted)">
										{pkg.description.slice(0, 80)}{pkg.description.length > 80 ? '...' : ''}
									</p>
								{/if}
							</button>
						</li>
					{/each}
				</ul>
			{/if}
		</div>

		<div class="mt-4 flex justify-end">
			<button
				type="button"
				onclick={oncancel}
				class="rounded px-4 py-2 text-sm"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				Cancel
			</button>
		</div>
	</dialog>
{/if}
