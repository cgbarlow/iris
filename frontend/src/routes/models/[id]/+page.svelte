<script lang="ts">
	import { page } from '$app/state';
	import { apiFetch } from '$lib/utils/api';
	import type { Model } from '$lib/types/api';

	let model = $state<Model | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let activeTab = $state<'overview' | 'canvas' | 'versions'>('overview');

	$effect(() => {
		const id = page.params.id;
		if (id) loadModel(id);
	});

	async function loadModel(id: string) {
		loading = true;
		error = null;
		try {
			const res: Response = await apiFetch(`/api/models/${id}`);
			if (res.ok) {
				model = await res.json();
			} else {
				error = `Model not found (${res.status})`;
			}
		} catch {
			error = 'Failed to load model';
		}
		loading = false;
	}
</script>

<svelte:head>
	<title>{model?.name ?? 'Model Detail'} — Iris</title>
</svelte:head>

<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
	<ol class="flex gap-1">
		<li><a href="/models" style="color: var(--color-primary)">Models</a></li>
		<li aria-hidden="true">/</li>
		<li aria-current="page">{model?.name ?? page.params.id}</li>
	</ol>
</nav>

{#if loading}
	<p style="color: var(--color-muted)">Loading model...</p>
{:else if error}
	<div role="alert" class="rounded border p-4" style="border-color: var(--color-danger); color: var(--color-danger)">
		{error}
	</div>
{:else if model}
	<h1 class="text-2xl font-bold" style="color: var(--color-fg)">{model.name}</h1>
	<p class="mt-1 text-sm" style="color: var(--color-muted)">{model.model_type}</p>

	<!-- Tab navigation -->
	<div class="mt-6 flex gap-1 border-b" style="border-color: var(--color-border)" role="tablist" aria-label="Model sections">
		<button
			role="tab"
			aria-selected={activeTab === 'overview'}
			onclick={() => (activeTab = 'overview')}
			class="px-4 py-2 text-sm"
			style="color: {activeTab === 'overview' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'overview' ? 'var(--color-primary)' : 'transparent'}"
		>
			Overview
		</button>
		<button
			role="tab"
			aria-selected={activeTab === 'canvas'}
			onclick={() => (activeTab = 'canvas')}
			class="px-4 py-2 text-sm"
			style="color: {activeTab === 'canvas' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'canvas' ? 'var(--color-primary)' : 'transparent'}"
		>
			Canvas
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
	</div>

	<div class="mt-4" role="tabpanel">
		{#if activeTab === 'overview'}
			<dl class="grid gap-4" style="grid-template-columns: auto 1fr">
				<dt class="text-sm font-medium" style="color: var(--color-muted)">ID</dt>
				<dd class="font-mono text-xs" style="color: var(--color-fg)">{model.id}</dd>

				<dt class="text-sm font-medium" style="color: var(--color-muted)">Type</dt>
				<dd style="color: var(--color-fg)">{model.model_type}</dd>

				<dt class="text-sm font-medium" style="color: var(--color-muted)">Version</dt>
				<dd style="color: var(--color-fg)">{model.current_version ?? 'N/A'}</dd>

				<dt class="text-sm font-medium" style="color: var(--color-muted)">Created</dt>
				<dd style="color: var(--color-fg)">{model.created_at ?? 'N/A'}</dd>

				{#if model.description}
					<dt class="text-sm font-medium" style="color: var(--color-muted)">Description</dt>
					<dd style="color: var(--color-fg)">{model.description}</dd>
				{/if}
			</dl>
		{:else if activeTab === 'canvas'}
			<p style="color: var(--color-muted)">Canvas view will render the model diagram here.</p>
		{:else if activeTab === 'versions'}
			<p style="color: var(--color-muted)">Version history will be displayed here.</p>
		{/if}
	</div>
{/if}
