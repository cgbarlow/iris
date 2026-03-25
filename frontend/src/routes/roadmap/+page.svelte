<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/stores/auth.svelte.js';
	import { getActiveSetId, getActiveSetName } from '$lib/stores/activeSet.svelte.js';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import { isSceniaEnabled, SceniaAdapter } from '$lib/scenia/adapter';
	import { openScenia } from '$lib/scenia/config.js';

	let extensionEnabled = $state<boolean | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let roadmapData = $state<Record<string, any> | null>(null);
	// Determine set ID from query param or active set
	const setId = $derived(page.url.searchParams.get('setId') ?? getActiveSetId() ?? '');
	const focusElementId = $derived(page.url.searchParams.get('focus'));

	// Available sets for set selector
	type SetOption = { id: string; name: string };
	let availableSets = $state<SetOption[]>([]);

	$effect(() => {
		if (!isAuthenticated()) {
			goto('/login');
			return;
		}
		checkExtension();
	});

	$effect(() => {
		if (extensionEnabled && setId) {
			loadRoadmapData(setId);
		}
	});

	async function checkExtension() {
		extensionEnabled = await isSceniaEnabled();
		if (!extensionEnabled) {
			loading = false;
			return;
		}

		// Load available sets
		try {
			const data = await apiFetch<{ items: SetOption[] }>('/api/sets');
			availableSets = data.items;
		} catch {
			availableSets = [];
		}
	}

	async function loadRoadmapData(sid: string) {
		loading = true;
		error = null;
		try {
			const adapter = new SceniaAdapter(sid);
			roadmapData = await adapter.getAppData();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load roadmap data';
		}
		loading = false;
	}

	function switchSet(newSetId: string) {
		goto(`/roadmap?setId=${newSetId}`);
	}

	function navigateToElement(elementId: string) {
		goto(`/elements/${elementId}`);
	}
</script>

<svelte:head>
	<title>Roadmap — Iris</title>
</svelte:head>

{#if extensionEnabled === false}
	<div class="flex flex-col items-center justify-center gap-4 py-20">
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Scenia Roadmapping</h1>
		<p style="color: var(--color-muted)">The Scenia extension is not installed.</p>
		<a
			href="/admin/settings/extensions"
			class="rounded px-4 py-2 text-sm font-medium text-white"
			style="background-color: var(--color-primary)"
		>
			Install Extension
		</a>
	</div>
{:else if extensionEnabled === null}
	<p style="color: var(--color-muted)">Checking extension status...</p>
{:else}
	<!-- Scenia header -->
	<div class="mb-6 flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Roadmap</h1>
			<p class="mt-1 text-sm" style="color: var(--color-muted)">Strategic roadmapping powered by Scenia</p>
		</div>
		<div class="flex items-center gap-3">
			<!-- Set selector -->
			<select
				onchange={(e) => switchSet((e.target as HTMLSelectElement).value)}
				class="rounded px-3 py-1.5 text-sm"
				style="background: var(--color-surface); border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				{#if !setId}
					<option value="">Select a set...</option>
				{/if}
				{#each availableSets as s}
					<option value={s.id} selected={s.id === setId}>{s.name}</option>
				{/each}
			</select>

			{#if setId}
				<button
					onclick={() => openScenia(setId)}
					class="rounded px-4 py-1.5 text-sm font-medium"
					style="border: 1px solid var(--color-success, #22c55e); color: var(--color-success, #22c55e); background: transparent; cursor: pointer"
				>
					View in Scenia
				</button>
			{/if}
		</div>
	</div>

	{#if error}
		<div
			class="mb-4 rounded border p-3 text-sm"
			style="background-color: rgba(239,68,68,0.1); border-color: var(--color-danger); color: var(--color-danger)"
		>
			{error}
		</div>
	{/if}

	{#if !setId}
		<div class="rounded border p-8 text-center" style="border-color: var(--color-border)">
			<p style="color: var(--color-muted)">Select a set to view its roadmap data.</p>
		</div>
	{:else if loading}
		<p style="color: var(--color-muted)">Loading roadmap data...</p>
	{:else if roadmapData}
		<!-- Roadmap data summary -->
		<div class="grid grid-cols-4 gap-4">
			<div class="rounded border p-4" style="border-color: var(--color-border)">
				<div class="text-2xl font-bold" style="color: var(--color-fg)">{roadmapData.strategies.length}</div>
				<div class="text-sm" style="color: var(--color-muted)">Strategies</div>
			</div>
			<div class="rounded border p-4" style="border-color: var(--color-border)">
				<div class="text-2xl font-bold" style="color: var(--color-fg)">{roadmapData.programmes.length}</div>
				<div class="text-sm" style="color: var(--color-muted)">Programmes</div>
			</div>
			<div class="rounded border p-4" style="border-color: var(--color-border)">
				<div class="text-2xl font-bold" style="color: var(--color-fg)">{roadmapData.initiatives.length}</div>
				<div class="text-sm" style="color: var(--color-muted)">Initiatives</div>
			</div>
			<div class="rounded border p-4" style="border-color: var(--color-border)">
				<div class="text-2xl font-bold" style="color: var(--color-fg)">{roadmapData.assets.length}</div>
				<div class="text-sm" style="color: var(--color-muted)">Assets</div>
			</div>
		</div>

		<!-- Entity tables -->
		{#if roadmapData.strategies.length > 0}
			<div class="mt-6">
				<h2 class="text-lg font-semibold" style="color: var(--color-fg)">Strategies</h2>
				<div class="mt-2 overflow-x-auto">
					<table class="w-full text-sm" style="color: var(--color-fg)">
						<thead>
							<tr style="border-bottom: 1px solid var(--color-border)">
								<th class="px-3 py-2 text-left font-medium" style="color: var(--color-muted)">Name</th>
								<th class="px-3 py-2 text-left font-medium" style="color: var(--color-muted)">Description</th>
								<th class="px-3 py-2 text-left font-medium" style="color: var(--color-muted)">Actions</th>
							</tr>
						</thead>
						<tbody>
							{#each roadmapData.strategies as entity}
								<tr style="border-bottom: 1px solid var(--color-border)">
									<td class="px-3 py-2">{entity.name}</td>
									<td class="px-3 py-2">{entity.description ?? ''}</td>
									<td class="px-3 py-2">
										<button onclick={() => navigateToElement(entity.id)} class="text-sm" style="color: var(--color-primary)">View in Iris</button>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		{/if}

		{#if roadmapData.programmes.length > 0}
			<div class="mt-6">
				<h2 class="text-lg font-semibold" style="color: var(--color-fg)">Programmes</h2>
				<div class="mt-2 overflow-x-auto">
					<table class="w-full text-sm" style="color: var(--color-fg)">
						<thead>
							<tr style="border-bottom: 1px solid var(--color-border)">
								<th class="px-3 py-2 text-left font-medium" style="color: var(--color-muted)">Name</th>
								<th class="px-3 py-2 text-left font-medium" style="color: var(--color-muted)">Description</th>
								<th class="px-3 py-2 text-left font-medium" style="color: var(--color-muted)">Budget</th>
								<th class="px-3 py-2 text-left font-medium" style="color: var(--color-muted)">Actions</th>
							</tr>
						</thead>
						<tbody>
							{#each roadmapData.programmes as entity}
								{@const d = entity as Record<string, unknown>}
								<tr style="border-bottom: 1px solid var(--color-border)">
									<td class="px-3 py-2">{entity.name}</td>
									<td class="px-3 py-2">{entity.description ?? ''}</td>
									<td class="px-3 py-2">{d.budget ? `$${Number(d.budget).toLocaleString()}` : '-'}</td>
									<td class="px-3 py-2">
										<button onclick={() => navigateToElement(entity.id)} class="text-sm" style="color: var(--color-primary)">View in Iris</button>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		{/if}

		{#if roadmapData.initiatives.length > 0}
			<div class="mt-6">
				<h2 class="text-lg font-semibold" style="color: var(--color-fg)">Initiatives</h2>
				<div class="mt-2 overflow-x-auto">
					<table class="w-full text-sm" style="color: var(--color-fg)">
						<thead>
							<tr style="border-bottom: 1px solid var(--color-border)">
								<th class="px-3 py-2 text-left font-medium" style="color: var(--color-muted)">Name</th>
								<th class="px-3 py-2 text-left font-medium" style="color: var(--color-muted)">Status</th>
								<th class="px-3 py-2 text-left font-medium" style="color: var(--color-muted)">Progress</th>
								<th class="px-3 py-2 text-left font-medium" style="color: var(--color-muted)">Budget</th>
								<th class="px-3 py-2 text-left font-medium" style="color: var(--color-muted)">Actions</th>
							</tr>
						</thead>
						<tbody>
							{#each roadmapData.initiatives as entity}
								{@const d = entity as Record<string, unknown>}
								<tr style="border-bottom: 1px solid var(--color-border)">
									<td class="px-3 py-2">{entity.name}</td>
									<td class="px-3 py-2">{d.status ?? '-'}</td>
									<td class="px-3 py-2">{d.progress ?? 0}%</td>
									<td class="px-3 py-2">{d.budget ? `$${Number(d.budget).toLocaleString()}` : '-'}</td>
									<td class="px-3 py-2">
										<button onclick={() => navigateToElement(entity.id)} class="text-sm" style="color: var(--color-primary)">View in Iris</button>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		{/if}

		{#if roadmapData.assets.length > 0}
			<div class="mt-6">
				<h2 class="text-lg font-semibold" style="color: var(--color-fg)">Assets</h2>
				<div class="mt-2 overflow-x-auto">
					<table class="w-full text-sm" style="color: var(--color-fg)">
						<thead>
							<tr style="border-bottom: 1px solid var(--color-border)">
								<th class="px-3 py-2 text-left font-medium" style="color: var(--color-muted)">Name</th>
								<th class="px-3 py-2 text-left font-medium" style="color: var(--color-muted)">Owner</th>
								<th class="px-3 py-2 text-left font-medium" style="color: var(--color-muted)">Maturity</th>
								<th class="px-3 py-2 text-left font-medium" style="color: var(--color-muted)">Actions</th>
							</tr>
						</thead>
						<tbody>
							{#each roadmapData.assets as entity}
								{@const d = entity as Record<string, unknown>}
								<tr style="border-bottom: 1px solid var(--color-border)">
									<td class="px-3 py-2">{entity.name}</td>
									<td class="px-3 py-2">{d.owner ?? '-'}</td>
									<td class="px-3 py-2">{d.maturityRating ?? '-'}/5</td>
									<td class="px-3 py-2">
										<button onclick={() => navigateToElement(entity.id)} class="text-sm" style="color: var(--color-primary)">View in Iris</button>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		{/if}

		<!-- Timeline info -->
		{#if roadmapData.timelineSettings}
			{@const ts = roadmapData.timelineSettings as Record<string, unknown>}
			<div class="mt-6 rounded border p-4" style="border-color: var(--color-border)">
				<h3 class="text-sm font-semibold" style="color: var(--color-fg)">Timeline</h3>
				<div class="mt-2 flex gap-4 text-sm" style="color: var(--color-muted)">
					<span>Start: {ts.startDate ?? '-'}</span>
					<span>Months: {ts.monthsToShow ?? '-'}</span>
				</div>
			</div>
		{/if}
	{/if}
{/if}
