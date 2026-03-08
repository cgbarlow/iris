<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import type {
		Element,
		ElementVersion,
		Relationship,
		RelationshipListResponse,
		ElementDiagramRef,
	} from '$lib/types/api';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import TagInput from '$lib/components/TagInput.svelte';
	import CommentsPanel from '$lib/components/CommentsPanel.svelte';
	import VersionHistory from '$lib/components/VersionHistory.svelte';
	import { Accordion } from 'bits-ui';
	import DOMPurify from 'dompurify';

	let entity = $state<Element | null>(null);
	let versions = $state<ElementVersion[]>([]);
	let relationships = $state<Relationship[]>([]);
	let usedInModels = $state<ElementDiagramRef[]>([]);
	let inheritedTags = $state<string[]>([]);
	let allTags = $state<string[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let activeTab = $state<'details' | 'versions' | 'relationships' | 'diagrams'>('details');
	let showDeleteDialog = $state(false);

	// Inline metadata editing state
	let editingDetails = $state(false);
	let detailsDirty = $state(false);
	let savingDetails = $state(false);
	let editName = $state('');
	let editDescription = $state('');
	let editTags = $state<string[]>([]);
	let editAttributes = $state<{name: string; type: string; scope: string; notes: string; lower_bound: string; upper_bound: string}[]>([]);

	// Loading states per tab
	let versionsLoading = $state(false);
	let relationshipsLoading = $state(false);
	let diagramsLoading = $state(false);

	$effect(() => {
		const id = page.params.id;
		if (id) loadEntity(id);
	});

	// Auto-enter edit mode when ?edit=true is in the URL
	$effect(() => {
		if (entity && !loading && page.url.searchParams.get('edit') === 'true') {
			enterDetailsEdit();
		}
	});

	// Track dirty state for inline editing
	$effect(() => {
		if (!editingDetails || !entity) return;
		const nameChanged = editName !== entity.name;
		const descChanged = editDescription !== (entity.description ?? '');
		const origTags = entity.tags ?? [];
		const tagsChanged = JSON.stringify(editTags.slice().sort()) !== JSON.stringify(origTags.slice().sort());
		const origAttrs = (entity.data as Record<string, unknown>)?.attributes;
		const attrsChanged = JSON.stringify(editAttributes) !== JSON.stringify(
			Array.isArray(origAttrs) ? origAttrs.map((a: any) => ({ name: a.name ?? '', type: a.type ?? '', scope: a.scope ?? 'Public', notes: a.notes ?? '', lower_bound: a.lower_bound ?? '', upper_bound: a.upper_bound ?? '' })) : []
		);
		detailsDirty = nameChanged || descChanged || tagsChanged || attrsChanged;
	});

	async function loadEntity(id: string) {
		loading = true;
		error = null;
		try {
			entity = await apiFetch<Element>(`/api/elements/${id}`);
			// Load tab data in parallel
			await Promise.all([
				loadVersions(id),
				loadRelationships(id),
				loadDiagrams(id),
				loadAllTags(),
			]);
		} catch (e) {
			error = e instanceof ApiError && e.status === 404
				? 'Element not found'
				: 'Failed to load element';
		}
		loading = false;
	}

	async function loadVersions(id: string) {
		versionsLoading = true;
		try {
			versions = await apiFetch<ElementVersion[]>(`/api/elements/${id}/versions`);
		} catch {
			versions = [];
		}
		versionsLoading = false;
	}

	async function loadRelationships(id: string) {
		relationshipsLoading = true;
		try {
			const data = await apiFetch<RelationshipListResponse>(`/api/relationships?element_id=${id}`);
			relationships = data.items;
		} catch {
			relationships = [];
		}
		relationshipsLoading = false;
	}

	async function loadDiagrams(id: string) {
		diagramsLoading = true;
		try {
			usedInModels = await apiFetch<ElementDiagramRef[]>(`/api/elements/${id}/diagrams`);
			// Compute inherited tags from diagrams this element appears in
			const diagramTags = new Set<string>();
			for (const ref of usedInModels) {
				try {
					const m = await apiFetch<{ tags?: string[] }>(`/api/diagrams/${ref.diagram_id}`);
					if (m.tags) m.tags.forEach((t) => diagramTags.add(t));
				} catch { /* skip inaccessible diagrams */ }
			}
			// Exclude own tags from inherited
			const ownTags = new Set(entity?.tags ?? []);
			inheritedTags = [...diagramTags].filter((t) => !ownTags.has(t)).sort();
		} catch {
			usedInModels = [];
			inheritedTags = [];
		}
		diagramsLoading = false;
	}

	async function loadAllTags() {
		try {
			allTags = await apiFetch<string[]>('/api/elements/tags/all');
		} catch {
			allTags = [];
		}
	}

	function enterDetailsEdit() {
		if (!entity) return;
		editName = entity.name;
		editDescription = entity.description ?? '';
		editTags = [...(entity.tags ?? [])];
		const srcAttrs = (entity.data as Record<string, unknown>)?.attributes;
		editAttributes = Array.isArray(srcAttrs)
			? srcAttrs.map((a: any) => ({ name: a.name ?? '', type: a.type ?? '', scope: a.scope ?? 'Public', notes: a.notes ?? '', lower_bound: a.lower_bound ?? '', upper_bound: a.upper_bound ?? '' }))
			: [];
		editingDetails = true;
		detailsDirty = false;
	}

	async function saveEntityMetadata() {
		if (!entity) return;
		savingDetails = true;
		error = null;
		try {
			const sanitizedName = DOMPurify.sanitize(editName).trim();
			const sanitizedDesc = DOMPurify.sanitize(editDescription).trim();
			if (!sanitizedName) {
				error = 'Name is required';
				savingDetails = false;
				return;
			}
			const updatedData = { ...(entity.data ?? {}) } as Record<string, unknown>;
			if (editAttributes.length > 0) {
				updatedData.attributes = editAttributes.filter(a => a.name.trim());
			} else {
				delete updatedData.attributes;
			}
			await apiFetch(`/api/elements/${entity.id}`, {
				method: 'PUT',
				headers: { 'If-Match': String(entity.current_version) },
				body: JSON.stringify({
					name: sanitizedName,
					element_type: entity.element_type,
					description: sanitizedDesc,
					data: updatedData,
					change_summary: 'Updated element details',
				}),
			});

			// Sync tags
			const oldTags = entity.tags ?? [];
			const toAdd = editTags.filter((t) => !oldTags.includes(t));
			const toRemove = oldTags.filter((t) => !editTags.includes(t));
			for (const tag of toAdd) {
				await apiFetch(`/api/elements/${entity.id}/tags`, {
					method: 'POST',
					body: JSON.stringify({ tag }),
				});
			}
			for (const tag of toRemove) {
				await apiFetch(`/api/elements/${entity.id}/tags/${encodeURIComponent(tag)}`, {
					method: 'DELETE',
				});
			}

			editingDetails = false;
			detailsDirty = false;
			await loadEntity(entity.id);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to update element';
		}
		savingDetails = false;
	}

	function discardDetailsChanges() {
		editingDetails = false;
		detailsDirty = false;
	}

	async function handleClone() {
		if (!entity) return;
		try {
			const created = await apiFetch<Element>('/api/elements', {
				method: 'POST',
				body: JSON.stringify({
					element_type: entity.element_type,
					name: `${entity.name} (Copy)`,
					description: entity.description ?? '',
					data: entity.data ?? {},
				}),
			});
			await goto(`/elements/${created.id}`);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to clone element';
		}
	}

	async function handleDelete() {
		if (!entity) return;
		try {
			await apiFetch(`/api/elements/${entity.id}`, {
				method: 'DELETE',
				headers: { 'If-Match': String(entity.current_version) },
			});
			showDeleteDialog = false;
			await goto('/elements');
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to delete element';
		}
	}
</script>

<svelte:head>
	<title>{entity?.name ?? 'Element Detail'} — Iris</title>
</svelte:head>

<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
	<ol class="flex flex-wrap items-baseline gap-1">
		<li><a href="/elements" style="color: var(--color-primary)">Elements</a></li>
		<li class="flex items-baseline gap-1">
			<span aria-hidden="true">/</span>
			<span aria-current="page">{entity?.name ?? page.params.id}</span>
		</li>
	</ol>
</nav>

{#if loading}
	<p style="color: var(--color-muted)">Loading element...</p>
{:else if error}
	<div role="alert" class="rounded border p-4" style="border-color: var(--color-danger); color: var(--color-danger)">
		{error}
	</div>
{:else if entity}
	<div class="flex items-center justify-between">
		<div>
			<div class="flex flex-wrap items-center gap-3">
				<h1 class="text-2xl font-bold" style="color: var(--color-fg)">{entity.name}</h1>
				{#if entity.set_name}
					<span class="rounded px-2 py-0.5 text-sm" style="background: var(--color-surface); color: var(--color-muted); border: 1px solid var(--color-border)">{entity.set_name}</span>
				{/if}
			</div>
			<p class="mt-1 text-sm flex items-center gap-2 flex-wrap" style="color: var(--color-muted)">
				<span>{entity.element_type}</span>
				{#if entity.notation && entity.notation !== 'simple'}
					<span class="rounded-full px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border)">{entity.notation}</span>
				{/if}
			</p>
		</div>
		<div class="flex gap-2">
			<button
				onclick={handleClone}
				class="rounded px-4 py-2 text-sm"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				Clone
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
	<div class="mt-6 flex gap-1 border-b" style="border-color: var(--color-border)" role="tablist" aria-label="Element sections">
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
			aria-selected={activeTab === 'diagrams'}
			onclick={() => (activeTab = 'diagrams')}
			class="px-4 py-2 text-sm"
			style="color: {activeTab === 'diagrams' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'diagrams' ? 'var(--color-primary)' : 'transparent'}"
		>
			Used In Diagrams
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
			aria-selected={activeTab === 'versions'}
			onclick={() => (activeTab = 'versions')}
			class="px-4 py-2 text-sm"
			style="color: {activeTab === 'versions' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'versions' ? 'var(--color-primary)' : 'transparent'}"
		>
			Version History
		</button>
	</div>

	<!-- Tab panels -->
	<div class="mt-4" role="tabpanel">
		{#if activeTab === 'details'}
			{@const modifiedByUsername = versions.length > 0 ? (versions[0].created_by_username ?? versions[0].created_by) : (entity.created_by_username ?? entity.created_by)}
			<!-- Inline edit toolbar -->
			<div class="mb-3 flex items-center gap-2">
				{#if editingDetails}
					<button
						onclick={saveEntityMetadata}
						disabled={!detailsDirty || savingDetails}
						class="rounded px-3 py-1.5 text-sm text-white disabled:opacity-50"
						style="background-color: var(--color-success, #16a34a)"
					>
						{savingDetails ? 'Saving...' : 'Save'}
					</button>
					<button
						onclick={discardDetailsChanges}
						class="rounded px-3 py-1.5 text-sm"
						style="border: 1px solid var(--color-border); color: var(--color-fg)"
					>
						Discard
					</button>
					{#if detailsDirty}
						<span class="text-xs" style="color: var(--color-muted)">Unsaved changes</span>
					{/if}
				{:else}
					<button
						onclick={enterDetailsEdit}
						class="rounded px-3 py-1.5 text-sm text-white"
						style="background-color: var(--color-primary)"
					>
						Edit Details
					</button>
				{/if}
			</div>

			<Accordion.Root type="single" value="summary">
				<!-- Overview group (open by default) -->
				<Accordion.Item value="summary" class="border-b" style="border-color: var(--color-border)">
					<Accordion.Header>
						<Accordion.Trigger class="group flex w-full items-center justify-between py-3 text-sm font-semibold" style="color: var(--color-fg)">
							Overview
							<span class="transition-transform duration-200 group-data-[state=open]:rotate-90" style="color: var(--color-muted); font-size: 0.75rem" aria-hidden="true">&#9654;</span>
						</Accordion.Trigger>
					</Accordion.Header>
					<Accordion.Content class="pb-4">
						<dl class="grid gap-3" style="grid-template-columns: auto 1fr">
							<dt class="text-sm font-medium" style="color: var(--color-muted)">Name</dt>
							<dd>
								{#if editingDetails}
									<input
										type="text"
										bind:value={editName}
										class="w-full rounded border px-2 py-1 text-sm"
										style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
									/>
								{:else}
									<span style="color: var(--color-fg)">{entity.name}</span>
								{/if}
							</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Description</dt>
							<dd>
								{#if editingDetails}
									<textarea
										bind:value={editDescription}
										rows="3"
										class="w-full rounded border px-2 py-1 text-sm"
										style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
									></textarea>
								{:else}
									<span style="color: var(--color-fg)">{entity.description ?? 'No description'}</span>
								{/if}
							</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Type</dt>
							<dd style="color: var(--color-fg)">{entity.element_type}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Notation</dt>
							<dd style="color: var(--color-fg)">{entity.notation ?? 'simple'}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Set</dt>
							<dd>
								<span class="rounded px-2 py-0.5 text-sm" style="background: var(--color-surface); color: var(--color-fg)">
									{entity.set_name ?? 'Default'}
								</span>
							</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Tags</dt>
							<dd>
								{#if editingDetails}
									<TagInput
										tags={editTags}
										onaddtag={(tag) => { editTags = [...editTags, tag]; }}
										onremovetag={(tag) => { editTags = editTags.filter(t => t !== tag); }}
										{inheritedTags}
										suggestions={allTags}
									/>
								{:else if (entity.tags ?? []).length > 0 || inheritedTags.length > 0}
									<div class="flex flex-wrap gap-1">
										{#each (entity.tags ?? []) as tag}
											<span class="rounded-full px-2 py-0.5 text-xs" style="background: var(--color-primary); color: white">{tag}</span>
										{/each}
										{#each inheritedTags as tag}
											<span class="rounded-full px-2 py-0.5 text-xs" style="background: var(--color-muted); color: white; opacity: 0.5" title="Inherited tag">{tag}</span>
										{/each}
									</div>
								{:else}
									<span style="color: var(--color-muted)">None</span>
								{/if}
							</dd>
						</dl>
					</Accordion.Content>
				</Accordion.Item>

				<!-- Attributes group -->
				{@const elemData = entity.data as Record<string, unknown> | null | undefined}
				{@const elemAttrs = Array.isArray(elemData?.attributes) ? elemData.attributes as {name: string; type: string; scope?: string; notes?: string; default?: string; lower_bound?: string; upper_bound?: string; stereotype?: string}[] : []}
				{#if elemAttrs.length > 0 || editingDetails}
					<Accordion.Item value="attributes" class="border-b" style="border-color: var(--color-border)">
						<Accordion.Header>
							<Accordion.Trigger class="group flex w-full items-center justify-between py-3 text-sm font-semibold" style="color: var(--color-fg)">
								Attributes ({editingDetails ? editAttributes.length : elemAttrs.length})
								<span class="transition-transform duration-200 group-data-[state=open]:rotate-90" style="color: var(--color-muted); font-size: 0.75rem" aria-hidden="true">&#9654;</span>
							</Accordion.Trigger>
						</Accordion.Header>
						<Accordion.Content class="pb-4">
							{#if editingDetails}
								<table class="w-full text-sm" style="color: var(--color-fg)">
									<thead>
										<tr style="border-bottom: 1px solid var(--color-border)">
											<th class="py-1 pr-2 text-left font-medium" style="color: var(--color-muted)">Scope</th>
											<th class="py-1 pr-2 text-left font-medium" style="color: var(--color-muted)">Name</th>
											<th class="py-1 pr-2 text-left font-medium" style="color: var(--color-muted)">Type</th>
											<th class="py-1 pr-2 text-left font-medium" style="color: var(--color-muted)">Lower</th>
											<th class="py-1 pr-2 text-left font-medium" style="color: var(--color-muted)">Upper</th>
											<th class="py-1 text-left font-medium" style="color: var(--color-muted)"></th>
										</tr>
									</thead>
									<tbody>
										{#each editAttributes as attr, i}
											<tr style="border-bottom: 1px solid var(--color-border)">
												<td class="py-1 pr-2">
													<select bind:value={attr.scope} class="w-full rounded border px-1 py-0.5 text-xs" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)">
														<option value="Public">+ Public</option>
														<option value="Private">- Private</option>
														<option value="Protected"># Protected</option>
														<option value="Package">~ Package</option>
													</select>
												</td>
												<td class="py-1 pr-2"><input type="text" bind:value={attr.name} class="w-full rounded border px-1 py-0.5 text-sm" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" placeholder="name" /></td>
												<td class="py-1 pr-2"><input type="text" bind:value={attr.type} class="w-full rounded border px-1 py-0.5 text-sm" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" placeholder="type" /></td>
												<td class="py-1 pr-2" style="width:3rem"><input type="text" bind:value={attr.lower_bound} class="w-full rounded border px-1 py-0.5 text-sm" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" placeholder="0" /></td>
												<td class="py-1 pr-2" style="width:3rem"><input type="text" bind:value={attr.upper_bound} class="w-full rounded border px-1 py-0.5 text-sm" style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)" placeholder="*" /></td>
												<td class="py-1">
													<button onclick={() => { editAttributes = editAttributes.filter((_, idx) => idx !== i); }} class="text-xs px-1 rounded" style="color: var(--color-danger)" title="Remove attribute">✕</button>
												</td>
											</tr>
										{/each}
									</tbody>
								</table>
								<button
									onclick={() => { editAttributes = [...editAttributes, {name: '', type: '', scope: 'Public', notes: '', lower_bound: '', upper_bound: ''}]; }}
									class="mt-2 rounded px-2 py-1 text-xs"
									style="border: 1px solid var(--color-border); color: var(--color-fg)"
								>
									+ Add Attribute
								</button>
							{:else}
								<table class="w-full text-sm" style="color: var(--color-fg)">
									<thead>
										<tr style="border-bottom: 1px solid var(--color-border)">
											<th class="py-1 pr-4 text-left font-medium" style="color: var(--color-muted)">Vis</th>
											<th class="py-1 pr-4 text-left font-medium" style="color: var(--color-muted)">Name</th>
											<th class="py-1 pr-4 text-left font-medium" style="color: var(--color-muted)">Type</th>
											<th class="py-1 pr-4 text-left font-medium" style="color: var(--color-muted)">Multiplicity</th>
											<th class="py-1 text-left font-medium" style="color: var(--color-muted)">Notes</th>
										</tr>
									</thead>
									<tbody>
										{#each elemAttrs as attr}
											<tr style="border-bottom: 1px solid var(--color-border)">
												<td class="py-1 pr-4 font-mono">{attr.scope === 'Private' ? '-' : attr.scope === 'Protected' ? '#' : attr.scope === 'Package' ? '~' : '+'}</td>
												<td class="py-1 pr-4 font-medium">{attr.name}</td>
												<td class="py-1 pr-4">{attr.type || '—'}</td>
												<td class="py-1 pr-4">{attr.lower_bound && attr.upper_bound ? `${attr.lower_bound}..${attr.upper_bound}` : '—'}</td>
												<td class="py-1 text-xs" style="color: var(--color-muted)">{attr.notes || ''}</td>
											</tr>
										{/each}
									</tbody>
								</table>
							{/if}
						</Accordion.Content>
					</Accordion.Item>
				{/if}

				<!-- Details group (collapsed) -->
				<Accordion.Item value="element-details" class="border-b" style="border-color: var(--color-border)">
					<Accordion.Header>
						<Accordion.Trigger class="group flex w-full items-center justify-between py-3 text-sm font-semibold" style="color: var(--color-fg)">
							Details
							<span class="transition-transform duration-200 group-data-[state=open]:rotate-90" style="color: var(--color-muted); font-size: 0.75rem" aria-hidden="true">&#9654;</span>
						</Accordion.Trigger>
					</Accordion.Header>
					<Accordion.Content class="pb-4">
						<dl class="grid gap-3" style="grid-template-columns: auto 1fr">
							<dt class="text-sm font-medium" style="color: var(--color-muted)">ID</dt>
							<dd class="text-sm" style="color: var(--color-fg)">{entity.id}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Version</dt>
							<dd style="color: var(--color-fg)">{entity.current_version ?? 'N/A'}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Created</dt>
							<dd style="color: var(--color-fg)">{entity.created_at ?? 'N/A'}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Created By</dt>
							<dd style="color: var(--color-fg)">{entity.created_by_username ?? entity.created_by}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Modified</dt>
							<dd style="color: var(--color-fg)">{entity.updated_at ?? 'N/A'}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Modified By</dt>
							<dd style="color: var(--color-fg)">{modifiedByUsername}</dd>

							{#if (entity.metadata as Record<string, unknown> | null | undefined)?.status}
								<dt class="text-sm font-medium" style="color: var(--color-muted)">Status</dt>
								<dd style="color: var(--color-fg)">{(entity.metadata as Record<string, unknown>).status}</dd>
							{/if}
						</dl>
					</Accordion.Content>
				</Accordion.Item>

				<!-- Extended group (collapsed) -->
				<Accordion.Item value="extended" class="border-b" style="border-color: var(--color-border)">
					<Accordion.Header>
						<Accordion.Trigger class="group flex w-full items-center justify-between py-3 text-sm font-semibold" style="color: var(--color-fg)">
							Extended
							<span class="transition-transform duration-200 group-data-[state=open]:rotate-90" style="color: var(--color-muted); font-size: 0.75rem" aria-hidden="true">&#9654;</span>
						</Accordion.Trigger>
					</Accordion.Header>
					<Accordion.Content class="pb-4">
						{@const meta = entity.metadata as Record<string, unknown> | null | undefined}
						{@const hasMeta = !!(meta && (meta.stereotype || meta.version || meta.scope || meta.abstract || meta.persistence || meta.author || meta.complexity || meta.phase || meta.created_date || meta.modified_date || meta.gen_type || (Array.isArray(meta.tagged_values) && (meta.tagged_values as unknown[]).length > 0)))}
						{#if hasMeta}
							<dl class="grid gap-3" style="grid-template-columns: auto 1fr">
								{#if meta?.stereotype}
									<dt class="text-sm font-medium" style="color: var(--color-muted)">Stereotype</dt>
									<dd style="color: var(--color-fg)">{meta.stereotype}</dd>
								{/if}
								{#if meta?.version}
									<dt class="text-sm font-medium" style="color: var(--color-muted)">Metadata Version</dt>
									<dd style="color: var(--color-fg)">{meta.version}</dd>
								{/if}
								{#if meta?.scope}
									<dt class="text-sm font-medium" style="color: var(--color-muted)">Scope</dt>
									<dd style="color: var(--color-fg)">{meta.scope}</dd>
								{/if}
								{#if meta?.abstract}
									<dt class="text-sm font-medium" style="color: var(--color-muted)">Abstract</dt>
									<dd style="color: var(--color-fg)">Yes</dd>
								{/if}
								{#if meta?.persistence}
									<dt class="text-sm font-medium" style="color: var(--color-muted)">Persistence</dt>
									<dd style="color: var(--color-fg)">{meta.persistence}</dd>
								{/if}
								{#if meta?.author}
									<dt class="text-sm font-medium" style="color: var(--color-muted)">Author</dt>
									<dd style="color: var(--color-fg)">{meta.author}</dd>
								{/if}
								{#if meta?.complexity}
									<dt class="text-sm font-medium" style="color: var(--color-muted)">Complexity</dt>
									<dd style="color: var(--color-fg)">{meta.complexity}</dd>
								{/if}
								{#if meta?.phase}
									<dt class="text-sm font-medium" style="color: var(--color-muted)">Phase</dt>
									<dd style="color: var(--color-fg)">{meta.phase}</dd>
								{/if}
								{#if meta?.created_date}
									<dt class="text-sm font-medium" style="color: var(--color-muted)">EA Created Date</dt>
									<dd style="color: var(--color-fg)">{meta.created_date}</dd>
								{/if}
								{#if meta?.modified_date}
									<dt class="text-sm font-medium" style="color: var(--color-muted)">EA Modified Date</dt>
									<dd style="color: var(--color-fg)">{meta.modified_date}</dd>
								{/if}
								{#if meta?.gen_type}
									<dt class="text-sm font-medium" style="color: var(--color-muted)">Gen Type</dt>
									<dd style="color: var(--color-fg)">{meta.gen_type}</dd>
								{/if}

								{#if Array.isArray(meta?.tagged_values) && (meta.tagged_values as unknown[]).length > 0}
									<dt class="text-sm font-medium" style="color: var(--color-muted)">Tagged Values</dt>
									<dd>
										<table class="w-full text-sm" style="color: var(--color-fg)">
											<thead>
												<tr style="border-bottom: 1px solid var(--color-border)">
													<th class="py-1 pr-4 text-left font-medium" style="color: var(--color-muted)">Property</th>
													<th class="py-1 text-left font-medium" style="color: var(--color-muted)">Value</th>
												</tr>
											</thead>
											<tbody>
												{#each meta.tagged_values as tv}
													{@const tvObj = tv as {property?: string; value?: string}}
													<tr style="border-bottom: 1px solid var(--color-border)">
														<td class="py-1 pr-4">{tvObj.property ?? ''}</td>
														<td class="py-1">{tvObj.value ?? ''}</td>
													</tr>
												{/each}
											</tbody>
										</table>
									</dd>
								{/if}
							</dl>
						{:else}
							<p class="text-sm" style="color: var(--color-muted)">No extended metadata available.</p>
						{/if}
					</Accordion.Content>
				</Accordion.Item>
			</Accordion.Root>
		{:else if activeTab === 'diagrams'}
			{#if diagramsLoading}
				<p style="color: var(--color-muted)">Loading diagrams...</p>
			{:else if usedInModels.length === 0}
				<p style="color: var(--color-muted)">Not used in any diagrams.</p>
			{:else}
				<ul class="flex flex-col gap-2">
					{#each usedInModels as model}
						<li>
							<a
								href="/diagrams/{model.diagram_id}"
								class="flex items-center gap-3 rounded border block p-3"
								style="border-color: var(--color-border); color: var(--color-primary)"
							>
								<span class="font-medium">{model.name}</span>
								<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
									{model.diagram_type}
								</span>
							</a>
						</li>
					{/each}
				</ul>
			{/if}
		{:else if activeTab === 'relationships'}
			{#if relationshipsLoading}
				<p style="color: var(--color-muted)">Loading relationships...</p>
			{:else if relationships.length === 0}
				<p style="color: var(--color-muted)">No relationships yet. Relationships are created automatically when elements are connected by edges in a diagram canvas.</p>
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
									<a href="/elements/{rel.source_element_id}" style="color: var(--color-primary)">
										{rel.source_element_id === entity.id ? entity.name : (rel.source_element_name || rel.source_element_id)}
									</a>
								</td>
								<td class="py-2">
									<a href="/elements/{rel.target_element_id}" style="color: var(--color-primary)">
										{rel.target_element_id === entity.id ? entity.name : (rel.target_element_name || rel.target_element_id)}
									</a>
								</td>
								<td class="py-2" style="color: var(--color-fg)">{rel.label ?? '—'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}
		{:else if activeTab === 'versions'}
			<VersionHistory {versions} loading={versionsLoading} />
		{/if}
	</div>

	<!-- Comments section -->
	<section class="mt-8">
		<CommentsPanel targetType="element" targetId={entity.id} />
	</section>

	<ConfirmDialog
		open={showDeleteDialog}
		title="Delete Element"
		message="Are you sure you want to delete '{entity.name}'? This action cannot be undone."
		confirmLabel="Delete"
		onconfirm={handleDelete}
		oncancel={() => (showDeleteDialog = false)}
	/>
{/if}
