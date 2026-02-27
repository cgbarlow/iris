<script lang="ts">
	import { apiFetch } from '$lib/utils/api';
	import type { Entity, PaginatedResponse } from '$lib/types/api';
	import { SIMPLE_ENTITY_TYPES } from '$lib/types/canvas';

	let entities = $state<Entity[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let searchQuery = $state('');
	let typeFilter = $state('');
	let sortField = $state<'name' | 'entity_type' | 'updated_at'>('name');

	$effect(() => {
		loadEntities();
	});

	async function loadEntities() {
		loading = true;
		try {
			const data = await apiFetch<PaginatedResponse<Entity>>('/api/entities');
			entities = data.items;
		} catch {
			error = 'Failed to load entities';
		}
		loading = false;
	}

	const filteredEntities = $derived(
		entities
			.filter((e) => {
				if (typeFilter && e.entity_type !== typeFilter) return false;
				if (searchQuery) {
					const q = searchQuery.toLowerCase();
					return (
						e.name.toLowerCase().includes(q) ||
						(e.description?.toLowerCase().includes(q) ?? false)
					);
				}
				return true;
			})
			.sort((a, b) => {
				if (sortField === 'name') return a.name.localeCompare(b.name);
				if (sortField === 'entity_type') return a.entity_type.localeCompare(b.entity_type);
				return (b.updated_at ?? '').localeCompare(a.updated_at ?? '');
			}),
	);
</script>

<svelte:head>
	<title>Entities — Iris</title>
</svelte:head>

<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Entities</h1>
<p class="mt-2" style="color: var(--color-muted)">Browse and manage architectural entities.</p>

<!-- Filters -->
<div class="mt-4 flex flex-wrap gap-3">
	<div>
		<label for="entity-search" class="sr-only">Search entities</label>
		<input
			id="entity-search"
			bind:value={searchQuery}
			type="search"
			placeholder="Search entities..."
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		/>
	</div>
	<div>
		<label for="entity-type-filter" class="sr-only">Filter by type</label>
		<select
			id="entity-type-filter"
			bind:value={typeFilter}
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		>
			<option value="">All types</option>
			{#each SIMPLE_ENTITY_TYPES as t}
				<option value={t.key}>{t.label}</option>
			{/each}
		</select>
	</div>
	<div>
		<label for="entity-sort" class="sr-only">Sort by</label>
		<select
			id="entity-sort"
			bind:value={sortField}
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		>
			<option value="name">Sort by name</option>
			<option value="entity_type">Sort by type</option>
			<option value="updated_at">Sort by updated</option>
		</select>
	</div>
</div>

<!-- Results -->
<div class="mt-4" aria-live="polite">
	{#if loading}
		<p style="color: var(--color-muted)">Loading entities...</p>
	{:else if error}
		<div role="alert" style="color: var(--color-danger)">{error}</div>
	{:else if filteredEntities.length === 0}
		<p style="color: var(--color-muted)">No entities found.</p>
	{:else}
		<p class="mb-3 text-sm" style="color: var(--color-muted)">
			{filteredEntities.length} entit{filteredEntities.length === 1 ? 'y' : 'ies'}
		</p>
		<ul class="flex flex-col gap-2">
			{#each filteredEntities as entity}
				<li>
					<a
						href="/entities/{entity.id}"
						class="flex items-center gap-3 rounded border p-3"
						style="border-color: var(--color-border); color: var(--color-fg)"
					>
						<span class="text-sm font-medium" style="color: var(--color-primary)">
							{entity.name}
						</span>
						<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
							{entity.entity_type}
						</span>
						{#if entity.description}
							<span class="text-xs" style="color: var(--color-muted)">
								{entity.description.slice(0, 60)}{entity.description.length > 60 ? '...' : ''}
							</span>
						{/if}
					</a>
				</li>
			{/each}
		</ul>
	{/if}
</div>
