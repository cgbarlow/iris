<script lang="ts">
	import { page } from '$app/state';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type { Model, ModelVersion } from '$lib/types/api';
	import BrowseCanvas from '$lib/canvas/BrowseCanvas.svelte';
	import ModelCanvas from '$lib/canvas/ModelCanvas.svelte';
	import { isEditMode } from '$lib/stores/canvasMode.svelte';
	import type { CanvasNode, CanvasEdge } from '$lib/types/canvas';

	let model = $state<Model | null>(null);
	let versions = $state<ModelVersion[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let activeTab = $state<'overview' | 'canvas' | 'versions'>('overview');
	let versionsLoading = $state(false);

	// Canvas data parsed from model.data
	let canvasNodes = $state<CanvasNode[]>([]);
	let canvasEdges = $state<CanvasEdge[]>([]);

	$effect(() => {
		const id = page.params.id;
		if (id) loadModel(id);
	});

	async function loadModel(id: string) {
		loading = true;
		error = null;
		try {
			model = await apiFetch<Model>(`/api/models/${id}`);
			parseCanvasData();
			loadVersions(id);
		} catch (e) {
			error = e instanceof ApiError && e.status === 404
				? 'Model not found'
				: 'Failed to load model';
		}
		loading = false;
	}

	function parseCanvasData() {
		if (!model?.data) {
			canvasNodes = [];
			canvasEdges = [];
			return;
		}
		const data = model.data as Record<string, unknown>;
		canvasNodes = (Array.isArray(data.nodes) ? data.nodes : []) as CanvasNode[];
		canvasEdges = (Array.isArray(data.edges) ? data.edges : []) as CanvasEdge[];
	}

	async function loadVersions(id: string) {
		versionsLoading = true;
		try {
			versions = await apiFetch<ModelVersion[]>(`/api/models/${id}/versions`);
		} catch {
			versions = [];
		}
		versionsLoading = false;
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
			{#if canvasNodes.length === 0}
				<div class="flex items-center justify-center rounded border p-8" style="border-color: var(--color-border); min-height: 300px">
					<p style="color: var(--color-muted)">No diagram data available for this model.</p>
				</div>
			{:else}
				<div style="height: 500px; border: 1px solid var(--color-border); border-radius: 0.375rem; overflow: hidden">
					{#if isEditMode()}
						<ModelCanvas nodes={canvasNodes} edges={canvasEdges} />
					{:else}
						<BrowseCanvas nodes={canvasNodes} edges={canvasEdges} />
					{/if}
				</div>
			{/if}
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
							<th class="py-2 text-left" style="color: var(--color-muted)">Date</th>
							<th class="py-2 text-left" style="color: var(--color-muted)">Change Summary</th>
						</tr>
					</thead>
					<tbody>
						{#each versions as v}
							<tr style="border-bottom: 1px solid var(--color-border)">
								<td class="py-2" style="color: var(--color-fg)">v{v.version}</td>
								<td class="py-2" style="color: var(--color-fg)">{v.change_type}</td>
								<td class="py-2" style="color: var(--color-fg)">{v.created_at}</td>
								<td class="py-2" style="color: var(--color-fg)">{v.change_summary ?? '—'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}
		{/if}
	</div>
{/if}
