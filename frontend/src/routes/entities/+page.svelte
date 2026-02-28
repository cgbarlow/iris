<script lang="ts">
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type { Entity, PaginatedResponse } from '$lib/types/api';
	import { SIMPLE_ENTITY_TYPES } from '$lib/types/canvas';
	import EntityDialog from '$lib/canvas/controls/EntityDialog.svelte';
	import type { SimpleEntityType } from '$lib/types/canvas';

	let entities = $state<Entity[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let searchQuery = $state('');
	let typeFilter = $state('');
	let sortField = $state<'name' | 'entity_type' | 'updated_at'>('name');
	let showCreateDialog = $state(false);
	let groupMode = $state<'none' | 'type' | 'tag'>(
		(typeof window !== 'undefined' &&
			(localStorage.getItem('iris-entities-group') as 'none' | 'type' | 'tag')) ||
			'none'
	);

	$effect(() => {
		loadEntities();
	});

	$effect(() => {
		if (typeof window !== 'undefined') {
			localStorage.setItem('iris-entities-group', groupMode);
		}
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

	async function handleCreate(name: string, entityType: SimpleEntityType, description: string) {
		try {
			await apiFetch<Entity>('/api/entities', {
				method: 'POST',
				body: JSON.stringify({
					entity_type: entityType,
					name,
					description,
					data: {},
				}),
			});
			showCreateDialog = false;
			await loadEntities();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create entity';
		}
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
			})
	);

	const groupedEntities = $derived.by(() => {
		const items = filteredEntities;
		if (groupMode === 'none') return [{ key: '', items }];

		const groups = new Map<string, Entity[]>();

		if (groupMode === 'type') {
			for (const e of items) {
				const key = e.entity_type;
				if (!groups.has(key)) groups.set(key, []);
				groups.get(key)!.push(e);
			}
		} else if (groupMode === 'tag') {
			const untagged: Entity[] = [];
			for (const e of items) {
				if (e.tags && e.tags.length > 0) {
					for (const tag of e.tags) {
						if (!groups.has(tag)) groups.set(tag, []);
						groups.get(tag)!.push(e);
					}
				} else {
					untagged.push(e);
				}
			}
			if (untagged.length > 0) groups.set('Untagged', untagged);
		}

		return [...groups.entries()]
			.sort(([a], [b]) => a.localeCompare(b))
			.map(([key, items]) => ({ key, items }));
	});
</script>

<svelte:head>
	<title>Entities — Iris</title>
</svelte:head>

<div class="flex items-center justify-between">
	<div>
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Entities</h1>
		<p class="mt-2" style="color: var(--color-muted)">Browse and manage architectural entities.</p>
	</div>
	<button
		onclick={() => (showCreateDialog = true)}
		class="rounded px-4 py-2 text-sm text-white"
		style="background-color: var(--color-primary)"
	>
		New Entity
	</button>
</div>

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
	<div>
		<label for="entity-group" class="sr-only">Group by</label>
		<select
			id="entity-group"
			bind:value={groupMode}
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		>
			<option value="none">Not grouped</option>
			<option value="type">By type</option>
			<option value="tag">By tag</option>
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
		{#each groupedEntities as group}
			{#if group.key}
				<details open class="mt-4">
					<summary class="cursor-pointer text-sm font-medium" style="color: var(--color-fg)">
						{group.key} ({group.items.length})
					</summary>
					<ul class="mt-2 flex flex-col gap-2">
						{#each group.items as entity}
							<li>
								<a
									href="/entities/{entity.id}"
									class="flex flex-wrap items-center gap-3 rounded border p-3"
									style="border-color: var(--color-border); color: var(--color-fg)"
								>
									<span class="text-sm font-medium" style="color: var(--color-primary)">{entity.name}</span>
									<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">{entity.entity_type}</span>
									{#if entity.tags && entity.tags.length > 0}
										{#each entity.tags as tag}
											<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-primary); color: white">{tag}</span>
										{/each}
									{/if}
									{#if entity.relationship_count}
										<span class="text-xs" style="color: var(--color-muted)">{entity.relationship_count} rel</span>
									{/if}
									{#if entity.model_usage_count}
										<span class="text-xs" style="color: var(--color-muted)">{entity.model_usage_count} model{entity.model_usage_count === 1 ? '' : 's'}</span>
									{/if}
									{#if entity.description}
										<span class="text-xs" style="color: var(--color-muted)">
											{entity.description.slice(0, 60)}{entity.description.length > 60 ? '...' : ''}
										</span>
									{/if}
								</a>
							</li>
						{/each}
					</ul>
				</details>
			{:else}
				<ul class="flex flex-col gap-2">
					{#each group.items as entity}
						<li>
							<a
								href="/entities/{entity.id}"
								class="flex flex-wrap items-center gap-3 rounded border p-3"
								style="border-color: var(--color-border); color: var(--color-fg)"
							>
								<span class="text-sm font-medium" style="color: var(--color-primary)">{entity.name}</span>
								<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">{entity.entity_type}</span>
								{#if entity.tags && entity.tags.length > 0}
									{#each entity.tags as tag}
										<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-primary); color: white">{tag}</span>
									{/each}
								{/if}
								{#if entity.relationship_count}
									<span class="text-xs" style="color: var(--color-muted)">{entity.relationship_count} rel</span>
								{/if}
								{#if entity.model_usage_count}
									<span class="text-xs" style="color: var(--color-muted)">{entity.model_usage_count} model{entity.model_usage_count === 1 ? '' : 's'}</span>
								{/if}
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
		{/each}
	{/if}
</div>

<EntityDialog
	open={showCreateDialog}
	mode="create"
	onsave={handleCreate}
	oncancel={() => (showCreateDialog = false)}
/>
