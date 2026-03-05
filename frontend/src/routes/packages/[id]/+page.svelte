<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import DiagramDialog from '$lib/components/DiagramDialog.svelte';
	import PackagePicker from '$lib/components/PackagePicker.svelte';
	import TreeNode from '$lib/components/TreeNode.svelte';
	import VersionHistory from '$lib/components/VersionHistory.svelte';
	import { Accordion } from 'bits-ui';
	import type { Bookmark, Diagram, DiagramHierarchyNode } from '$lib/types/api';

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
	let parentPackageName = $state<string | null>(null);
	let versions = $state<PackageVersion[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let activeTab = $state<'details' | 'versions'>('details');
	let showDeleteDialog = $state(false);
	let deleteMessage = $state('Are you sure you want to delete this package? This action cannot be undone.');
	let cloneLoading = $state(false);
	let isBookmarked = $state(false);
	let bookmarkLoading = $state(false);
	let showParentPicker = $state(false);
	let showChildMenu = $state(false);
	let showCreateChildDiagramDialog = $state(false);
	let showCreateChildPackageDialog = $state(false);
	let childPackageName = $state('');
	let childPackageDescription = $state('');

	// Inline metadata editing state
	let editingDetails = $state(false);
	let detailsDirty = $state(false);
	let savingDetails = $state(false);
	let editName = $state('');
	let editDescription = $state('');

	// Loading states
	let versionsLoading = $state(false);

	// Hierarchy sidebar state
	let sidebarOpen = $state(
		typeof localStorage !== 'undefined' && localStorage.getItem('iris-hierarchy-sidebar-open') === 'true'
	);
	let hierarchyTree = $state<DiagramHierarchyNode[]>([]);
	let hierarchyLoading = $state(false);
	let treeSearchQuery = $state('');
	let treeDiagramsOnly = $state(false);
	let treeExpandedIds = $state(new Set<string>());

	$effect(() => {
		const id = page.params.id;
		if (id) {
			loadPackage(id);
			loadBookmarkStatus(id);
		}
	});

	// Auto-load hierarchy tree when page loads with sidebar open
	$effect(() => {
		if (pkg && sidebarOpen && hierarchyTree.length === 0) {
			loadHierarchyTree();
		}
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
		parentPackageName = null;
		try {
			pkg = await apiFetch<Package>(`/api/packages/${id}`);
			await loadVersions(id);
			if (pkg.parent_package_id) {
				try {
					const parent = await apiFetch<Package>(`/api/packages/${pkg.parent_package_id}`);
					parentPackageName = parent.name;
				} catch {
					parentPackageName = null;
				}
			}
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

	async function confirmDelete() {
		if (!pkg) return;
		try {
			const counts = await apiFetch<{ child_packages: number; child_diagrams: number }>(
				`/api/packages/${pkg.id}/descendants/count`
			);
			if (counts.child_packages > 0 || counts.child_diagrams > 0) {
				const parts: string[] = [];
				if (counts.child_packages > 0) {
					parts.push(`${counts.child_packages} child package${counts.child_packages === 1 ? '' : 's'}`);
				}
				if (counts.child_diagrams > 0) {
					parts.push(`${counts.child_diagrams} diagram${counts.child_diagrams === 1 ? '' : 's'}`);
				}
				deleteMessage = `This will also delete ${parts.join(' and ')}. Are you sure?`;
			} else {
				deleteMessage = 'Are you sure you want to delete this package? This action cannot be undone.';
			}
		} catch {
			deleteMessage = 'Are you sure you want to delete this package? This action cannot be undone.';
		}
		showDeleteDialog = true;
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

	async function loadHierarchyTree() {
		if (!pkg?.set_id) return;
		hierarchyLoading = true;
		try {
			hierarchyTree = await apiFetch<DiagramHierarchyNode[]>(
				`/api/diagrams/hierarchy?set_id=${pkg.set_id}`
			);
		} catch {
			hierarchyTree = [];
		}
		hierarchyLoading = false;
	}

	async function loadBookmarkStatus(id: string) {
		try {
			const bookmarks = await apiFetch<Bookmark[]>('/api/bookmarks');
			isBookmarked = bookmarks.some((b) => b.package_id === id);
		} catch {
			isBookmarked = false;
		}
	}

	async function toggleBookmark() {
		if (!pkg || bookmarkLoading) return;
		bookmarkLoading = true;
		try {
			if (isBookmarked) {
				await apiFetch(`/api/packages/${pkg.id}/bookmark`, { method: 'DELETE' });
				isBookmarked = false;
			} else {
				await apiFetch(`/api/packages/${pkg.id}/bookmark`, { method: 'POST' });
				isBookmarked = true;
			}
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to update bookmark';
		}
		bookmarkLoading = false;
	}

	async function handleSetParent(parentPkg: { id: string }) {
		if (!pkg) return;
		showParentPicker = false;
		try {
			await apiFetch(`/api/packages/${pkg.id}/parent`, {
				method: 'PUT',
				body: JSON.stringify({ parent_package_id: parentPkg.id }),
			});
			await loadPackage(pkg.id);
			await loadHierarchyTree();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to change parent package';
		}
	}

	async function handleRemoveParent() {
		if (!pkg) return;
		try {
			await apiFetch(`/api/packages/${pkg.id}/parent`, {
				method: 'PUT',
				body: JSON.stringify({ parent_package_id: null }),
			});
			await loadPackage(pkg.id);
			await loadHierarchyTree();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to remove parent package';
		}
	}

	async function handleClone() {
		if (!pkg || cloneLoading) return;
		cloneLoading = true;
		try {
			const created = await apiFetch<{ id: string }>('/api/packages', {
				method: 'POST',
				body: JSON.stringify({
					name: `${pkg.name} (Copy)`,
					description: pkg.description,
					parent_package_id: pkg.parent_package_id,
					set_id: pkg.set_id,
					metadata: pkg.metadata,
				}),
			});
			await goto(`/packages/${created.id}`);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to clone package';
		}
		cloneLoading = false;
	}

	async function handleCreateChildDiagram(name: string, diagramType: string, description: string, _tags?: string[], _isTemplate?: boolean, childNotation?: string) {
		if (!pkg) return;
		try {
			const body: Record<string, unknown> = {
				diagram_type: diagramType,
				name,
				description,
				data: {},
				parent_package_id: pkg.id,
				set_id: pkg.set_id,
			};
			if (childNotation) body.notation = childNotation;
			const created = await apiFetch<Diagram>('/api/diagrams', {
				method: 'POST',
				body: JSON.stringify(body),
			});
			showCreateChildDiagramDialog = false;
			await loadHierarchyTree();
			await goto(`/diagrams/${created.id}`);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create child diagram';
		}
	}

	async function handleCreateChildPackage() {
		if (!pkg || !childPackageName.trim()) return;
		try {
			const created = await apiFetch<{ id: string }>('/api/packages', {
				method: 'POST',
				body: JSON.stringify({
					name: childPackageName.trim(),
					description: childPackageDescription.trim() || null,
					parent_package_id: pkg.id,
					set_id: pkg.set_id,
				}),
			});
			showCreateChildPackageDialog = false;
			childPackageName = '';
			childPackageDescription = '';
			await loadHierarchyTree();
			await goto(`/packages/${created.id}`);
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to create child package';
		}
	}

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
		localStorage.setItem('iris-hierarchy-sidebar-open', String(sidebarOpen));
		if (sidebarOpen && hierarchyTree.length === 0) {
			loadHierarchyTree();
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
	<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
		<ol class="flex flex-wrap items-baseline gap-1">
			<li><a href="/" style="color: var(--color-primary)">Packages</a></li>
			{#if pkg.parent_package_id}
				<li class="flex items-baseline gap-1">
					<span aria-hidden="true">/</span>
					<a href="/packages/{pkg.parent_package_id}" style="color: var(--color-primary)">{parentPackageName ?? pkg.parent_package_id}</a>
				</li>
			{/if}
			<li class="flex items-baseline gap-1">
				<span aria-hidden="true">/</span>
				<span aria-current="page">{pkg.name}</span>
			</li>
		</ol>
	</nav>
	<div class="flex items-center justify-between">
		<div>
			<div class="flex flex-wrap items-center gap-3">
				<h1 class="text-2xl font-bold" style="color: var(--color-fg)">{pkg.name}</h1>
				{#if pkg.set_name}
					<span class="rounded px-2 py-0.5 text-sm" style="background: var(--color-surface); color: var(--color-muted); border: 1px solid var(--color-border)">{pkg.set_name}</span>
				{/if}
			</div>
			<p class="mt-1 text-sm" style="color: var(--color-muted)">Package</p>
		</div>
		<div class="flex gap-2">
			<button
				onclick={toggleBookmark}
				disabled={bookmarkLoading}
				class="rounded px-4 py-2 text-sm"
				style="border: 1px solid {isBookmarked ? 'var(--color-primary)' : 'var(--color-border)'}; color: {isBookmarked ? 'var(--color-primary)' : 'var(--color-fg)'}; background: {isBookmarked ? 'var(--color-surface, transparent)' : 'transparent'}"
			>
				{isBookmarked ? 'Bookmarked' : 'Bookmark'}
			</button>
			<button
				onclick={handleClone}
				disabled={cloneLoading}
				class="rounded px-4 py-2 text-sm"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				{cloneLoading ? 'Cloning...' : 'Clone'}
			</button>
			<button
				onclick={confirmDelete}
				class="rounded px-4 py-2 text-sm text-white"
				style="background-color: var(--color-danger)"
			>
				Delete
			</button>
		</div>
	</div>

	<div class="mt-6 flex gap-4">
		<!-- Collapsible hierarchy sidebar -->
		{#if sidebarOpen}
			<aside
				style="width: 280px; max-height: calc(100vh - 80px); flex-shrink: 0"
				class="overflow-y-auto rounded border"
				style:border-color="var(--color-border)"
				style:background-color="var(--color-surface)"
				aria-label="Package hierarchy"
			>
				<div class="flex items-center justify-between p-3" style="border-bottom: 1px solid var(--color-border)">
					<span class="text-sm font-semibold" style="color: var(--color-fg)">Hierarchy</span>
					<div class="flex items-center gap-1">
						<button
							onclick={() => (treeDiagramsOnly = !treeDiagramsOnly)}
							class="rounded px-2 py-1 text-xs"
							style="border: 1px solid {treeDiagramsOnly ? 'var(--color-primary)' : 'var(--color-border)'}; color: {treeDiagramsOnly ? 'var(--color-primary)' : 'var(--color-fg)'}; background: {treeDiagramsOnly ? 'var(--color-surface, transparent)' : 'transparent'}"
							title="Show only items with child diagrams"
							aria-pressed={treeDiagramsOnly}
						>
							Diagrams
						</button>
						<div style="position: relative">
							<button
								onclick={() => (showChildMenu = !showChildMenu)}
								class="rounded px-2 py-1 text-xs"
								style="background: var(--color-primary); color: white"
								title="Create child item"
							>
								+ Child
							</button>
							{#if showChildMenu}
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<div
									style="position: fixed; inset: 0; z-index: 9"
									onclick={() => (showChildMenu = false)}
									onkeydown={(e) => { if (e.key === 'Escape') showChildMenu = false; }}
								></div>
								<div
									style="position: absolute; top: 100%; right: 0; z-index: 10; min-width: 120px"
									class="mt-1 rounded border shadow-md"
									style:border-color="var(--color-border)"
									style:background-color="var(--color-surface)"
								>
									<button
										onclick={() => { showCreateChildDiagramDialog = true; showChildMenu = false; }}
										class="block w-full px-3 py-2 text-left text-xs hover:opacity-80"
										style="color: var(--color-fg)"
									>
										Diagram
									</button>
									<button
										onclick={() => { showCreateChildPackageDialog = true; showChildMenu = false; }}
										class="block w-full px-3 py-2 text-left text-xs hover:opacity-80"
										style="color: var(--color-fg); border-top: 1px solid var(--color-border)"
									>
										Package
									</button>
								</div>
							{/if}
						</div>
						<button
							onclick={() => { sidebarOpen = false; localStorage.setItem('iris-hierarchy-sidebar-open', 'false'); }}
							class="rounded p-1 text-xs"
							style="color: var(--color-muted)"
							aria-label="Close sidebar"
						>
							✕
						</button>
					</div>
				</div>
				<div class="p-2">
					<input
						type="search"
						placeholder="Search tree..."
						bind:value={treeSearchQuery}
						class="w-full rounded border px-2 py-1 text-xs"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						aria-label="Search hierarchy"
					/>
				</div>
				<div class="px-2 pb-2">
					{#if hierarchyLoading}
						<p class="p-2 text-xs" style="color: var(--color-muted)">Loading...</p>
					{:else if hierarchyTree.length === 0}
						<p class="p-2 text-xs" style="color: var(--color-muted)">No diagrams in this set.</p>
					{:else}
						<ul role="tree">
							{#each hierarchyTree as node (node.id)}
								<TreeNode {node} currentDiagramId={pkg.id} searchQuery={treeSearchQuery} showDiagramsOnly={treeDiagramsOnly} expandedIds={treeExpandedIds} />
							{/each}
						</ul>
					{/if}
				</div>
			</aside>
		{/if}

		<!-- Main content -->
		<div class="min-w-0 flex-1">
		<!-- Tab navigation with hierarchy toggle -->
		<div class="flex items-center gap-1 border-b" style="border-color: var(--color-border)">
			<button onclick={toggleSidebar} aria-label="Toggle hierarchy sidebar" aria-pressed={sidebarOpen} class="rounded p-1">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="20" height="20"
					style="color: {sidebarOpen ? 'var(--color-primary)' : 'var(--color-muted)'}">
					<path d="M176,152h32a16,16,0,0,0,16-16V104a16,16,0,0,0-16-16H176a16,16,0,0,0-16,16v8H88V80h8a16,16,0,0,0,16-16V32A16,16,0,0,0,96,16H64A16,16,0,0,0,48,32V64A16,16,0,0,0,64,80h8V192a24,24,0,0,0,24,24h64v8a16,16,0,0,0,16,16h32a16,16,0,0,0,16-16V192a16,16,0,0,0-16-16H176a16,16,0,0,0-16,16v8H96a8,8,0,0,1-8-8V128h72v8A16,16,0,0,0,176,152ZM64,32H96V64H64ZM176,192h32v32H176Zm0-88h32v32H176Z"/>
				</svg>
			</button>
			<div class="flex gap-1" role="tablist" aria-label="Package sections">
				<button
					role="tab"
					aria-selected={activeTab === 'details'}
					onclick={() => { activeTab = 'details'; }}
					class="px-4 py-2 text-sm"
					style="color: {activeTab === 'details' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'details' ? 'var(--color-primary)' : 'transparent'}"
				>
					Details
				</button>
				<button
					role="tab"
					aria-selected={activeTab === 'versions'}
					onclick={() => { activeTab = 'versions'; }}
					class="px-4 py-2 text-sm"
					style="color: {activeTab === 'versions' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab === 'versions' ? 'var(--color-primary)' : 'transparent'}"
				>
					Version History
				</button>
			</div>
		</div>

		<div class="mt-4" role="tabpanel">
		{#if activeTab === 'details'}
			<div class="mb-3 flex items-center gap-2">
				{#if editingDetails}
					<button
						onclick={saveDetails}
						disabled={!detailsDirty || savingDetails}
						class="rounded px-3 py-1.5 text-sm text-white disabled:opacity-50"
						style="background-color: var(--color-success, #16a34a)"
					>
						{savingDetails ? 'Saving...' : 'Save'}
					</button>
					<button
						onclick={cancelDetailsEdit}
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

							<dt class="text-sm font-medium" style="color: var(--color-muted)">Parent Package</dt>
							<dd class="flex items-center gap-2">
								{#if pkg.parent_package_id}
									<a
										href="/packages/{pkg.parent_package_id}"
										class="text-sm underline"
										style="color: var(--color-primary)"
									>
										{parentPackageName ?? pkg.parent_package_id}
									</a>
								{:else}
									<span class="text-sm" style="color: var(--color-muted)">None — root package</span>
								{/if}
								<button
									onclick={() => (showParentPicker = true)}
									class="rounded px-2 py-0.5 text-xs"
									style="border: 1px solid var(--color-border); color: var(--color-primary)"
								>
									Change
								</button>
								{#if pkg.parent_package_id}
									<button
										onclick={handleRemoveParent}
										class="rounded px-2 py-0.5 text-xs"
										style="border: 1px solid var(--color-border); color: var(--color-danger)"
									>
										Remove
									</button>
								{/if}
							</dd>

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
			<VersionHistory {versions} loading={versionsLoading} />
		{/if}
		</div><!-- /tabpanel -->
		</div><!-- /flex-1 main content -->
	</div><!-- /flex gap-4 wrapper -->

	<ConfirmDialog
		open={showDeleteDialog}
		title="Delete Package"
		message={deleteMessage}
		confirmLabel="Delete"
		onconfirm={deletePackage}
		oncancel={() => { showDeleteDialog = false; }}
	/>

	<DiagramDialog
		open={showCreateChildDiagramDialog}
		mode="create"
		initialName=""
		initialType="component"
		initialDescription=""
		onsave={handleCreateChildDiagram}
		oncancel={() => (showCreateChildDiagramDialog = false)}
	/>

	{#if showCreateChildPackageDialog}
		<div style="position: fixed; inset: 0; z-index: 50; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.4)">
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<div
				class="rounded-lg p-6 shadow-lg"
				style="background: var(--color-bg); border: 1px solid var(--color-border); width: 400px; max-width: 90vw"
				onkeydown={(e) => { if (e.key === 'Escape') { showCreateChildPackageDialog = false; childPackageName = ''; childPackageDescription = ''; } }}
			>
				<h3 class="mb-4 text-lg font-semibold" style="color: var(--color-fg)">Create Package</h3>
				<label class="mb-1 block text-sm font-medium" style="color: var(--color-fg)">
					Name
					<input
						type="text"
						bind:value={childPackageName}
						class="mt-1 block w-full rounded border px-3 py-2 text-sm"
						style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-fg)"
						placeholder="Package name"
					/>
				</label>
				<label class="mb-4 mt-3 block text-sm font-medium" style="color: var(--color-fg)">
					Description
					<textarea
						bind:value={childPackageDescription}
						rows="3"
						class="mt-1 block w-full rounded border px-3 py-2 text-sm"
						style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-fg)"
						placeholder="Optional description"
					></textarea>
				</label>
				<div class="flex justify-end gap-2">
					<button
						onclick={() => { showCreateChildPackageDialog = false; childPackageName = ''; childPackageDescription = ''; }}
						class="rounded px-4 py-2 text-sm"
						style="border: 1px solid var(--color-border); color: var(--color-fg)"
					>
						Cancel
					</button>
					<button
						onclick={handleCreateChildPackage}
						disabled={!childPackageName.trim()}
						class="rounded px-4 py-2 text-sm text-white disabled:opacity-50"
						style="background: var(--color-primary)"
					>
						Create
					</button>
				</div>
			</div>
		</div>
	{/if}

	<PackagePicker
		open={showParentPicker}
		onselect={handleSetParent}
		oncancel={() => (showParentPicker = false)}
		excludePackageId={pkg.id}
		title="Select Parent Package"
		subtitle="Choose a package to contain this package."
	/>
{/if}
