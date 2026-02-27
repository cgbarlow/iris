<script lang="ts">
	import { page } from '$app/state';
	import { apiFetch } from '$lib/utils/api';
	import type { Entity } from '$lib/types/api';

	let entity = $state<Entity | null>(null);
	let versions = $state<Array<{ version: number; created_at: string; change_summary: string }>>([]);
	let relationships = $state<
		Array<{ id: string; type: string; source_name: string; target_name: string }>
	>([]);
	let usedInModels = $state<Array<{ id: string; name: string }>>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let activeTab = $state<'details' | 'versions' | 'relationships' | 'models'>('details');

	$effect(() => {
		const id = page.params.id;
		if (id) loadEntity(id);
	});

	async function loadEntity(id: string) {
		loading = true;
		error = null;
		try {
			const res: Response = await apiFetch(`/api/entities/${id}`);
			if (res.ok) {
				entity = await res.json();
			} else {
				error = `Entity not found (${res.status})`;
			}
		} catch {
			error = 'Failed to load entity';
		}
		loading = false;
	}
</script>

<svelte:head>
	<title>{entity?.name ?? 'Entity Detail'} — Iris</title>
</svelte:head>

<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
	<ol class="flex gap-1">
		<li><a href="/entities" style="color: var(--color-primary)">Entities</a></li>
		<li aria-hidden="true">/</li>
		<li aria-current="page">{entity?.name ?? page.params.id}</li>
	</ol>
</nav>

{#if loading}
	<p style="color: var(--color-muted)">Loading entity...</p>
{:else if error}
	<div role="alert" class="rounded border p-4" style="border-color: var(--color-danger); color: var(--color-danger)">
		{error}
	</div>
{:else if entity}
	<h1 class="text-2xl font-bold" style="color: var(--color-fg)">{entity.name}</h1>
	<p class="mt-1 text-sm" style="color: var(--color-muted)">{entity.entity_type}</p>

	<!-- Tab navigation -->
	<div class="mt-6 flex gap-1 border-b" style="border-color: var(--color-border)" role="tablist" aria-label="Entity sections">
		<button
			role="tab"
			aria-selected={activeTab === 'details'}
			onclick={() => (activeTab = 'details')}
			class="px-4 py-2 text-sm"
			style="color: {activeTab === 'details' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'details' ? 'var(--color-primary)' : 'transparent'}"
		>
			Details
		</button>
		<button
			role="tab"
			aria-selected={activeTab === 'versions'}
			onclick={() => (activeTab = 'versions')}
			class="px-4 py-2 text-sm"
			style="color: {activeTab === 'versions' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'versions' ? 'var(--color-primary)' : 'transparent'}"
		>
			Version History
		</button>
		<button
			role="tab"
			aria-selected={activeTab === 'relationships'}
			onclick={() => (activeTab = 'relationships')}
			class="px-4 py-2 text-sm"
			style="color: {activeTab === 'relationships' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'relationships' ? 'var(--color-primary)' : 'transparent'}"
		>
			Relationships
		</button>
		<button
			role="tab"
			aria-selected={activeTab === 'models'}
			onclick={() => (activeTab = 'models')}
			class="px-4 py-2 text-sm"
			style="color: {activeTab === 'models' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'models' ? 'var(--color-primary)' : 'transparent'}"
		>
			Used In Models
		</button>
	</div>

	<!-- Tab panels -->
	<div class="mt-4" role="tabpanel">
		{#if activeTab === 'details'}
			<dl class="grid gap-4" style="grid-template-columns: auto 1fr">
				<dt class="text-sm font-medium" style="color: var(--color-muted)">ID</dt>
				<dd class="font-mono text-xs" style="color: var(--color-fg)">{entity.id}</dd>

				<dt class="text-sm font-medium" style="color: var(--color-muted)">Type</dt>
				<dd style="color: var(--color-fg)">{entity.entity_type}</dd>

				<dt class="text-sm font-medium" style="color: var(--color-muted)">Version</dt>
				<dd style="color: var(--color-fg)">{entity.current_version ?? 'N/A'}</dd>

				<dt class="text-sm font-medium" style="color: var(--color-muted)">Created</dt>
				<dd style="color: var(--color-fg)">{entity.created_at ?? 'N/A'}</dd>

				{#if entity.description}
					<dt class="text-sm font-medium" style="color: var(--color-muted)">Description</dt>
					<dd style="color: var(--color-fg)">{entity.description}</dd>
				{/if}
			</dl>
		{:else if activeTab === 'versions'}
			{#if versions.length === 0}
				<p style="color: var(--color-muted)">No version history available.</p>
			{:else}
				<table class="w-full text-sm">
					<thead>
						<tr style="border-bottom: 1px solid var(--color-border)">
							<th class="py-2 text-left" style="color: var(--color-muted)">Version</th>
							<th class="py-2 text-left" style="color: var(--color-muted)">Date</th>
							<th class="py-2 text-left" style="color: var(--color-muted)">Change Summary</th>
						</tr>
					</thead>
					<tbody>
						{#each versions as v}
							<tr style="border-bottom: 1px solid var(--color-border)">
								<td class="py-2" style="color: var(--color-fg)">v{v.version}</td>
								<td class="py-2" style="color: var(--color-fg)">{v.created_at}</td>
								<td class="py-2" style="color: var(--color-fg)">{v.change_summary}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}
		{:else if activeTab === 'relationships'}
			{#if relationships.length === 0}
				<p style="color: var(--color-muted)">No relationships found.</p>
			{:else}
				<ul class="flex flex-col gap-2">
					{#each relationships as rel}
						<li
							class="rounded border p-3"
							style="border-color: var(--color-border); color: var(--color-fg)"
						>
							<span class="font-medium">{rel.source_name}</span>
							<span style="color: var(--color-muted)"> —{rel.type}→ </span>
							<span class="font-medium">{rel.target_name}</span>
						</li>
					{/each}
				</ul>
			{/if}
		{:else if activeTab === 'models'}
			{#if usedInModels.length === 0}
				<p style="color: var(--color-muted)">Not used in any models.</p>
			{:else}
				<ul class="flex flex-col gap-2">
					{#each usedInModels as model}
						<li>
							<a
								href="/models/{model.id}"
								class="rounded border block p-3"
								style="border-color: var(--color-border); color: var(--color-primary)"
							>
								{model.name}
							</a>
						</li>
					{/each}
				</ul>
			{/if}
		{/if}
	</div>
{/if}
