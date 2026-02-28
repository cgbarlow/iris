<script lang="ts">
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type { Model, PaginatedResponse } from '$lib/types/api';
	import ModelDialog from '$lib/components/ModelDialog.svelte';

	let models = $state<Model[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let searchQuery = $state('');
	let sortField = $state<'name' | 'model_type' | 'updated_at'>('name');
	let typeFilter = $state<string>('');
	let showCreateDialog = $state(false);

	$effect(() => {
		loadModels();
	});

	async function loadModels() {
		loading = true;
		try {
			const data = await apiFetch<PaginatedResponse<Model>>('/api/models');
			models = data.items;
		} catch {
			error = 'Failed to load models';
		}
		loading = false;
	}

	async function handleCreate(name: string, modelType: string, description: string) {
		try {
			await apiFetch<Model>('/api/models', {
				method: 'POST',
				body: JSON.stringify({
					model_type: modelType,
					name,
					description,
					data: {},
				}),
			});
			showCreateDialog = false;
			await loadModels();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create model';
		}
	}

	const filteredModels = $derived(
		models
			.filter((m) => {
				if (typeFilter && m.model_type.toLowerCase() !== typeFilter.toLowerCase()) {
					return false;
				}
				if (searchQuery) {
					const q = searchQuery.toLowerCase();
					return (
						m.name.toLowerCase().includes(q) ||
						(m.description?.toLowerCase().includes(q) ?? false)
					);
				}
				return true;
			})
			.sort((a, b) => {
				if (sortField === 'name') return a.name.localeCompare(b.name);
				if (sortField === 'model_type') return a.model_type.localeCompare(b.model_type);
				return (b.updated_at ?? '').localeCompare(a.updated_at ?? '');
			}),
	);
</script>

<svelte:head>
	<title>Models — Iris</title>
</svelte:head>

<div class="flex items-center justify-between">
	<div>
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Models</h1>
		<p class="mt-2" style="color: var(--color-muted)">Browse and manage architectural models.</p>
	</div>
	<button
		onclick={() => (showCreateDialog = true)}
		class="rounded px-4 py-2 text-sm text-white"
		style="background-color: var(--color-primary)"
	>
		New Model
	</button>
</div>

<!-- Filters -->
<div class="mt-4 flex flex-wrap gap-3">
	<div>
		<label for="model-search" class="sr-only">Search models</label>
		<input
			id="model-search"
			bind:value={searchQuery}
			type="search"
			placeholder="Search models..."
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		/>
	</div>
	<div>
		<label for="model-type-filter" class="sr-only">Filter by type</label>
		<select
			id="model-type-filter"
			bind:value={typeFilter}
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		>
			<option value="">All</option>
			<option value="simple">Simple</option>
			<option value="component">Component</option>
			<option value="sequence">Sequence</option>
			<option value="uml">UML</option>
			<option value="archimate">ArchiMate</option>
		</select>
	</div>
	<div>
		<label for="model-sort" class="sr-only">Sort by</label>
		<select
			id="model-sort"
			bind:value={sortField}
			class="rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		>
			<option value="name">Sort by name</option>
			<option value="model_type">Sort by type</option>
			<option value="updated_at">Sort by updated</option>
		</select>
	</div>
</div>

<!-- Results -->
<div class="mt-4" aria-live="polite">
	{#if loading}
		<p style="color: var(--color-muted)">Loading models...</p>
	{:else if error}
		<div role="alert" style="color: var(--color-danger)">{error}</div>
	{:else if filteredModels.length === 0}
		<p style="color: var(--color-muted)">No models found.</p>
	{:else}
		<p class="mb-3 text-sm" style="color: var(--color-muted)">
			{filteredModels.length} model{filteredModels.length === 1 ? '' : 's'}
		</p>
		<ul class="flex flex-col gap-2">
			{#each filteredModels as model}
				<li>
					<a
						href="/models/{model.id}"
						class="flex items-center gap-3 rounded border p-3"
						style="border-color: var(--color-border); color: var(--color-fg)"
					>
						<span class="text-sm font-medium" style="color: var(--color-primary)">
							{model.name}
						</span>
						<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
							{model.model_type}
						</span>
						{#if model.description}
							<span class="text-xs" style="color: var(--color-muted)">
								{model.description.slice(0, 60)}{model.description.length > 60 ? '...' : ''}
							</span>
						{/if}
					</a>
				</li>
			{/each}
		</ul>
	{/if}
</div>

<ModelDialog
	open={showCreateDialog}
	mode="create"
	onsave={handleCreate}
	oncancel={() => (showCreateDialog = false)}
/>
