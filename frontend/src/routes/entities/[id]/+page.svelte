<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type {
		Entity,
		EntityVersion,
		Relationship,
		RelationshipListResponse,
		EntityModelRef,
	} from '$lib/types/api';
	import EntityDialog from '$lib/canvas/controls/EntityDialog.svelte';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import type { SimpleEntityType } from '$lib/types/canvas';
	import CommentsPanel from '$lib/components/CommentsPanel.svelte';

	let entity = $state<Entity | null>(null);
	let versions = $state<EntityVersion[]>([]);
	let relationships = $state<Relationship[]>([]);
	let usedInModels = $state<EntityModelRef[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let activeTab = $state<'details' | 'versions' | 'relationships' | 'models'>('details');
	let showEditDialog = $state(false);
	let showDeleteDialog = $state(false);

	// Loading states per tab
	let versionsLoading = $state(false);
	let relationshipsLoading = $state(false);
	let modelsLoading = $state(false);

	$effect(() => {
		const id = page.params.id;
		if (id) loadEntity(id);
	});

	async function loadEntity(id: string) {
		loading = true;
		error = null;
		try {
			entity = await apiFetch<Entity>(`/api/entities/${id}`);
			// Load tab data in parallel
			await Promise.all([
				loadVersions(id),
				loadRelationships(id),
				loadModels(id),
			]);
		} catch (e) {
			error = e instanceof ApiError && e.status === 404
				? 'Entity not found'
				: 'Failed to load entity';
		}
		loading = false;
	}

	async function loadVersions(id: string) {
		versionsLoading = true;
		try {
			versions = await apiFetch<EntityVersion[]>(`/api/entities/${id}/versions`);
		} catch {
			versions = [];
		}
		versionsLoading = false;
	}

	async function loadRelationships(id: string) {
		relationshipsLoading = true;
		try {
			const data = await apiFetch<RelationshipListResponse>(`/api/relationships?entity_id=${id}`);
			relationships = data.items;
		} catch {
			relationships = [];
		}
		relationshipsLoading = false;
	}

	async function loadModels(id: string) {
		modelsLoading = true;
		try {
			usedInModels = await apiFetch<EntityModelRef[]>(`/api/entities/${id}/models`);
		} catch {
			usedInModels = [];
		}
		modelsLoading = false;
	}

	async function handleEdit(name: string, type: SimpleEntityType, description: string) {
		if (!entity) return;
		try {
			await apiFetch(`/api/entities/${entity.id}`, {
				method: 'PUT',
				headers: { 'If-Match': String(entity.current_version) },
				body: JSON.stringify({
					name,
					entity_type: type,
					description,
					change_summary: 'Updated entity details',
				}),
			});
			showEditDialog = false;
			await loadEntity(entity.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to update entity';
		}
	}

	async function handleDelete() {
		if (!entity) return;
		try {
			await apiFetch(`/api/entities/${entity.id}`, {
				method: 'DELETE',
				headers: { 'If-Match': String(entity.current_version) },
			});
			showDeleteDialog = false;
			await goto('/entities');
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to delete entity';
		}
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
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold" style="color: var(--color-fg)">{entity.name}</h1>
			<p class="mt-1 text-sm" style="color: var(--color-muted)">{entity.entity_type}</p>
		</div>
		<div class="flex gap-2">
			<button
				onclick={() => (showEditDialog = true)}
				class="rounded px-4 py-2 text-sm"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				Edit
			</button>
			<button
				onclick={() => (showDeleteDialog = true)}
				class="rounded px-4 py-2 text-sm text-white"
				style="background-color: var(--color-danger)"
			>
				Delete
			</button>
		</div>
	</div>

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

				<dt class="text-sm font-medium" style="color: var(--color-muted)">Created By</dt>
				<dd style="color: var(--color-fg)">{entity.created_by_username ?? entity.created_by}</dd>

				<dt class="text-sm font-medium" style="color: var(--color-muted)">Modified</dt>
				<dd style="color: var(--color-fg)">{entity.updated_at ?? 'N/A'}</dd>

				{#if entity.description}
					<dt class="text-sm font-medium" style="color: var(--color-muted)">Description</dt>
					<dd style="color: var(--color-fg)">{entity.description}</dd>
				{/if}
			</dl>
		{:else if activeTab === 'versions'}
			{#if versionsLoading}
				<p style="color: var(--color-muted)">Loading versions...</p>
			{:else if versions.length === 0}
				<p style="color: var(--color-muted)">No version history available.</p>
			{:else}
				<table class="w-full text-sm">
					<thead>
						<tr style="border-bottom: 1px solid var(--color-border)">
							<th class="py-2 text-left" style="color: var(--color-muted)">Version</th>
							<th class="py-2 text-left" style="color: var(--color-muted)">Type</th>
							<th class="py-2 text-left" style="color: var(--color-muted)">User</th>
							<th class="py-2 text-left" style="color: var(--color-muted)">Date</th>
							<th class="py-2 text-left" style="color: var(--color-muted)">Change Summary</th>
						</tr>
					</thead>
					<tbody>
						{#each versions as v}
							<tr style="border-bottom: 1px solid var(--color-border)">
								<td class="py-2" style="color: var(--color-fg)">v{v.version}</td>
								<td class="py-2" style="color: var(--color-fg)">{v.change_type}</td>
								<td class="py-2" style="color: var(--color-fg)">{v.created_by_username ?? v.created_by}</td>
								<td class="py-2" style="color: var(--color-fg)">{v.created_at}</td>
								<td class="py-2" style="color: var(--color-fg)">{v.change_summary ?? '—'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}
		{:else if activeTab === 'relationships'}
			{#if relationshipsLoading}
				<p style="color: var(--color-muted)">Loading relationships...</p>
			{:else if relationships.length === 0}
				<p style="color: var(--color-muted)">No relationships found.</p>
			{:else}
				<table class="w-full text-sm">
					<thead>
						<tr style="border-bottom: 1px solid var(--color-border)">
							<th class="py-2 text-left" style="color: var(--color-muted)">Type</th>
							<th class="py-2 text-left" style="color: var(--color-muted)">Source</th>
							<th class="py-2 text-left" style="color: var(--color-muted)">Target</th>
							<th class="py-2 text-left" style="color: var(--color-muted)">Label</th>
						</tr>
					</thead>
					<tbody>
						{#each relationships as rel}
							<tr style="border-bottom: 1px solid var(--color-border)">
								<td class="py-2" style="color: var(--color-fg)">{rel.relationship_type}</td>
								<td class="py-2">
									<a href="/entities/{rel.source_entity_id}" style="color: var(--color-primary)">
										{rel.source_entity_id === entity.id ? entity.name : rel.source_entity_id}
									</a>
								</td>
								<td class="py-2">
									<a href="/entities/{rel.target_entity_id}" style="color: var(--color-primary)">
										{rel.target_entity_id === entity.id ? entity.name : rel.target_entity_id}
									</a>
								</td>
								<td class="py-2" style="color: var(--color-fg)">{rel.label ?? '—'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}
		{:else if activeTab === 'models'}
			{#if modelsLoading}
				<p style="color: var(--color-muted)">Loading models...</p>
			{:else if usedInModels.length === 0}
				<p style="color: var(--color-muted)">Not used in any models.</p>
			{:else}
				<ul class="flex flex-col gap-2">
					{#each usedInModels as model}
						<li>
							<a
								href="/models/{model.model_id}"
								class="flex items-center gap-3 rounded border block p-3"
								style="border-color: var(--color-border); color: var(--color-primary)"
							>
								<span class="font-medium">{model.name}</span>
								<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
									{model.model_type}
								</span>
							</a>
						</li>
					{/each}
				</ul>
			{/if}
		{/if}
	</div>

	<!-- Comments section -->
	<section class="mt-8">
		<CommentsPanel targetType="entity" targetId={entity.id} />
	</section>

	<EntityDialog
		open={showEditDialog}
		mode="edit"
		initialName={entity.name}
		initialType={entity.entity_type as SimpleEntityType}
		initialDescription={entity.description ?? ''}
		onsave={handleEdit}
		oncancel={() => (showEditDialog = false)}
	/>

	<ConfirmDialog
		open={showDeleteDialog}
		title="Delete Entity"
		message="Are you sure you want to delete '{entity.name}'? This action cannot be undone."
		confirmLabel="Delete"
		onconfirm={handleDelete}
		oncancel={() => (showDeleteDialog = false)}
	/>
{/if}
