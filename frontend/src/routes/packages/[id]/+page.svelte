<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import { Accordion } from 'bits-ui';

	interface Package {
		id: string;
		current_version: number;
		name: string;
		description: string | null;
		created_at: string;
		created_by: string;
		created_by_username?: string;
		updated_at: string;
		is_deleted: boolean;
		parent_package_id: string | null;
		set_id: string | null;
		set_name: string | null;
		metadata: Record<string, unknown> | null;
	}

	interface PackageVersion {
		package_id: string;
		version: number;
		name: string;
		description: string | null;
		data: Record<string, unknown>;
		metadata: Record<string, unknown> | null;
		change_type: string;
		change_summary: string | null;
		created_at: string;
		created_by: string;
		created_by_username?: string;
	}

	let pkg = $state<Package | null>(null);
	let versions = $state<PackageVersion[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let activeTab = $state<'details' | 'versions'>('details');
	let showDeleteDialog = $state(false);

	// Inline metadata editing state
	let editingDetails = $state(false);
	let detailsDirty = $state(false);
	let savingDetails = $state(false);
	let editName = $state('');
	let editDescription = $state('');

	// Loading states
	let versionsLoading = $state(false);

	$effect(() => {
		const id = page.params.id;
		if (id) loadPackage(id);
	});

	// Track dirty state for inline editing
	$effect(() => {
		if (!editingDetails || !pkg) return;
		const nameChanged = editName !== pkg.name;
		const descChanged = editDescription !== (pkg.description ?? '');
		detailsDirty = nameChanged || descChanged;
	});

	async function loadPackage(id: string) {
		loading = true;
		error = null;
		try {
			pkg = await apiFetch<Package>(`/api/packages/${id}`);
			await loadVersions(id);
		} catch (e) {
			error = e instanceof ApiError && e.status === 404
				? 'Package not found'
				: 'Failed to load package';
		}
		loading = false;
	}

	async function loadVersions(id: string) {
		versionsLoading = true;
		try {
			versions = await apiFetch<PackageVersion[]>(`/api/packages/${id}/versions`);
		} catch {
			versions = [];
		}
		versionsLoading = false;
	}

	function enterDetailsEdit() {
		if (!pkg) return;
		editName = pkg.name;
		editDescription = pkg.description ?? '';
		editingDetails = true;
		detailsDirty = false;
	}

	function cancelDetailsEdit() {
		editingDetails = false;
		detailsDirty = false;
	}

	async function saveDetails() {
		if (!pkg || !detailsDirty) return;
		savingDetails = true;
		try {
			await apiFetch(`/api/packages/${pkg.id}`, {
				method: 'PUT',
				headers: { 'If-Match': String(pkg.current_version) },
				body: JSON.stringify({
					name: editName,
					description: editDescription || null,
					change_summary: 'Updated package details',
					metadata: pkg.metadata,
				}),
			});
			await loadPackage(pkg.id);
			editingDetails = false;
			detailsDirty = false;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to save';
		}
		savingDetails = false;
	}

	async function deletePackage() {
		if (!pkg) return;
		try {
			await apiFetch(`/api/packages/${pkg.id}`, {
				method: 'DELETE',
				headers: { 'If-Match': String(pkg.current_version) },
			});
			goto('/');
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to delete';
		}
	}
</script>

<svelte:head>
	<title>{pkg?.name ?? 'Package'} — Iris</title>
</svelte:head>

{#if loading}
	<div class="flex items-center justify-center p-8" role="status">
		<p style="color: var(--color-muted)">Loading package...</p>
	</div>
{:else if error}
	<div class="p-8" role="alert">
		<p style="color: var(--color-danger)">{error}</p>
		<button
			class="mt-4 rounded px-4 py-2 text-sm"
			style="background: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border)"
			onclick={() => goto('/')}
		>
			Back to Dashboard
		</button>
	</div>
{:else if pkg}
	<div class="mx-auto max-w-5xl p-6">
		<!-- Header -->
		<div class="mb-6 flex items-center justify-between">
			<div>
				<h1 class="text-2xl font-bold" style="color: var(--color-fg)">{pkg.name}</h1>
				<p class="mt-1 text-sm" style="color: var(--color-muted)">
					Package
					{#if pkg.set_name}
						&middot; {pkg.set_name}
					{/if}
				</p>
			</div>
			<div class="flex gap-2">
				<button
					class="rounded px-3 py-1.5 text-sm"
					style="background: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border)"
					onclick={() => { showDeleteDialog = true; }}
				>
					Delete
				</button>
			</div>
		</div>

		<!-- Tabs -->
		<div class="mb-4 flex gap-4 border-b" style="border-color: var(--color-border)">
			<button
				class="border-b-2 px-1 pb-2 text-sm font-medium transition-colors"
				style="border-color: {activeTab === 'details' ? 'var(--color-primary)' : 'transparent'}; color: {activeTab === 'details' ? 'var(--color-primary)' : 'var(--color-muted)'}"
				onclick={() => { activeTab = 'details'; }}
			>
				Details
			</button>
			<button
				class="border-b-2 px-1 pb-2 text-sm font-medium transition-colors"
				style="border-color: {activeTab === 'versions' ? 'var(--color-primary)' : 'transparent'}; color: {activeTab === 'versions' ? 'var(--color-primary)' : 'var(--color-muted)'}"
				onclick={() => { activeTab = 'versions'; }}
			>
				Version History
			</button>
		</div>

		<!-- Tab content -->
		{#if activeTab === 'details'}
			<div class="mb-4 flex items-center justify-between">
				<h2 class="sr-only">Package Details</h2>
				{#if editingDetails}
					<div class="flex gap-2">
						<button
							class="rounded px-3 py-1.5 text-sm"
							style="background: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border)"
							onclick={cancelDetailsEdit}
						>
							Cancel
						</button>
						<button
							class="rounded px-3 py-1.5 text-sm text-white disabled:opacity-50"
							style="background-color: var(--color-primary)"
							disabled={!detailsDirty || savingDetails}
							onclick={saveDetails}
						>
							{savingDetails ? 'Saving...' : 'Save'}
						</button>
					</div>
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
									<span style="color: var(--color-fg)">{pkg.name}</span>
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
									<span style="color: var(--color-fg)">{pkg.description ?? 'No description'}</span>
								{/if}
							</dd>

							{#if pkg.parent_package_id}
								<dt class="text-sm font-medium" style="color: var(--color-muted)">Parent Package</dt>
								<dd>
									<a
										href="/packages/{pkg.parent_package_id}"
										class="text-sm underline"
										style="color: var(--color-primary)"
									>
										{pkg.parent_package_id}
									</a>
								</dd>
							{/if}

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Set</dt>
							<dd>
								<span class="rounded px-2 py-0.5 text-sm" style="background: var(--color-surface); color: var(--color-fg)">
									{pkg.set_name ?? 'Default'}
								</span>
							</dd>
						</dl>
					</Accordion.Content>
				</Accordion.Item>

				<!-- Details group (collapsed) -->
				<Accordion.Item value="package-details" class="border-b" style="border-color: var(--color-border)">
					<Accordion.Header>
						<Accordion.Trigger class="group flex w-full items-center justify-between py-3 text-sm font-semibold" style="color: var(--color-fg)">
							Details
							<span class="transition-transform duration-200 group-data-[state=open]:rotate-90" style="color: var(--color-muted); font-size: 0.75rem" aria-hidden="true">&#9654;</span>
						</Accordion.Trigger>
					</Accordion.Header>
					<Accordion.Content class="pb-4">
						<dl class="grid gap-3" style="grid-template-columns: auto 1fr">
							<dt class="text-sm font-medium" style="color: var(--color-muted)">ID</dt>
							<dd class="text-sm" style="color: var(--color-fg)">{pkg.id}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Version</dt>
							<dd style="color: var(--color-fg)">{pkg.current_version ?? 'N/A'}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Created</dt>
							<dd style="color: var(--color-fg)">{pkg.created_at ?? 'N/A'}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Created By</dt>
							<dd style="color: var(--color-fg)">{pkg.created_by_username ?? pkg.created_by}</dd>

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Modified</dt>
							<dd style="color: var(--color-fg)">{pkg.updated_at ?? 'N/A'}</dd>

							{#if (pkg.metadata as Record<string, unknown> | null | undefined)?.status}
								<dt class="text-sm font-medium" style="color: var(--color-muted)">Status</dt>
								<dd style="color: var(--color-fg)">{(pkg.metadata as Record<string, unknown>).status}</dd>
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
						{@const meta = pkg.metadata as Record<string, unknown> | null | undefined}
						{@const hasMeta = !!(meta && (meta.ea_guid || meta.stereotype || meta.version || meta.scope || meta.author || meta.complexity || meta.phase || meta.created_date || meta.modified_date || meta.gen_type || (Array.isArray(meta.tagged_values) && (meta.tagged_values as unknown[]).length > 0)))}
						{#if hasMeta}
							<dl class="grid gap-3" style="grid-template-columns: auto 1fr">
								{#if meta?.ea_guid}
									<dt class="text-sm font-medium" style="color: var(--color-muted)">EA GUID</dt>
									<dd class="text-sm font-mono" style="color: var(--color-fg)">{meta.ea_guid}</dd>
								{/if}
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
		{:else if activeTab === 'versions'}
			{#if versionsLoading}
				<p style="color: var(--color-muted)">Loading versions...</p>
			{:else if versions.length === 0}
				<p style="color: var(--color-muted)">No version history.</p>
			{:else}
				<div class="space-y-3">
					{#each versions as v}
						<div class="rounded border p-3" style="border-color: var(--color-border); background: var(--color-surface)">
							<div class="flex items-center justify-between">
								<span class="text-sm font-medium" style="color: var(--color-fg)">
									v{v.version} — {v.change_type}
								</span>
								<span class="text-xs" style="color: var(--color-muted)">{v.created_at}</span>
							</div>
							{#if v.change_summary}
								<p class="mt-1 text-sm" style="color: var(--color-muted)">{v.change_summary}</p>
							{/if}
							<p class="mt-1 text-xs" style="color: var(--color-muted)">
								by {v.created_by_username ?? v.created_by}
							</p>
						</div>
					{/each}
				</div>
			{/if}
		{/if}
	</div>

	<ConfirmDialog
		open={showDeleteDialog}
		title="Delete Package"
		message="Are you sure you want to delete this package? This action cannot be undone."
		confirmLabel="Delete"
		onconfirm={deletePackage}
		oncancel={() => { showDeleteDialog = false; }}
	/>
{/if}
