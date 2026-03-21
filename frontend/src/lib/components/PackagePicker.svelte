<script lang="ts">
	/**
	 * Hierarchy-based package picker dialog.
	 * Uses the same tree structure as the sidebar hierarchy navigation (DRY).
	 * Click to select a package node, then OK to confirm. Supports creating new child packages.
	 */
	import { apiFetch } from '$lib/utils/api';
	import type { DiagramHierarchyNode, Package } from '$lib/types/api';

	interface Props {
		open: boolean;
		onselect: (pkg: Package) => void;
		oncancel: () => void;
		excludePackageId?: string;
		setId?: string;
		title?: string;
		subtitle?: string;
	}

	let {
		open,
		onselect,
		oncancel,
		excludePackageId,
		setId,
		title = 'Select Package',
		subtitle = 'Click a package to select it, then click OK.',
	}: Props = $props();

	let hierarchy = $state<DiagramHierarchyNode[]>([]);
	let search = $state('');
	let loading = $state(false);
	let dialogEl: HTMLDialogElement | undefined = $state();
	let selectedId = $state<string | null>(null);
	let selectedName = $state('');
	let expandedIds = $state(new Set<string>());

	// New package creation
	let showNewForm = $state(false);
	let newPkgName = $state('');
	let newPkgSaving = $state(false);
	let newPkgError = $state<string | null>(null);

	$effect(() => {
		if (open && dialogEl && !dialogEl.open) {
			search = '';
			selectedId = null;
			selectedName = '';
			showNewForm = false;
			newPkgName = '';
			newPkgError = null;
			expandedIds = new Set<string>();
			dialogEl.showModal();
			loadHierarchy();
		} else if (!open && dialogEl?.open) {
			dialogEl.close();
		}
	});

	async function loadHierarchy() {
		loading = true;
		try {
			const url = setId
				? `/api/diagrams/hierarchy?set_id=${encodeURIComponent(setId)}`
				: '/api/diagrams/hierarchy';
			hierarchy = await apiFetch<DiagramHierarchyNode[]>(url);
		} catch {
			hierarchy = [];
		}
		loading = false;
	}

	function matchesSearch(node: DiagramHierarchyNode): boolean {
		if (!search) return true;
		const q = search.toLowerCase();
		if (node.name.toLowerCase().includes(q)) return true;
		return (node.children ?? []).some(c => matchesSearch(c));
	}

	function selectNode(node: DiagramHierarchyNode) {
		if (node.node_type !== 'package') return;
		if (node.id === excludePackageId) return;
		if (selectedId === node.id) {
			selectedId = null;
			selectedName = '';
		} else {
			selectedId = node.id;
			selectedName = node.name;
		}
	}

	function confirmSelection() {
		if (!selectedId) return;
		// Construct a minimal Package object for the callback
		onselect({ id: selectedId, name: selectedName } as Package);
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			oncancel();
		}
	}

	function toggleExpand(id: string) {
		if (expandedIds.has(id)) {
			expandedIds.delete(id);
		} else {
			expandedIds.add(id);
		}
		expandedIds = new Set(expandedIds); // trigger reactivity
	}

	async function createNewPackage() {
		const name = newPkgName.trim();
		if (!name) return;
		newPkgSaving = true;
		newPkgError = null;
		try {
			const body: Record<string, unknown> = { name };
			if (selectedId) body.parent_package_id = selectedId;
			if (setId) body.set_id = setId;
			const created = await apiFetch<Package>('/api/packages', {
				method: 'POST',
				body: JSON.stringify(body),
			});
			await loadHierarchy();
			// Auto-select the new package
			selectedId = created.id;
			selectedName = created.name;
			// Expand parent so new package is visible
			if (selectedId) expandedIds.add(selectedId);
			expandedIds = new Set(expandedIds);
			showNewForm = false;
			newPkgName = '';
		} catch (e) {
			newPkgError = e instanceof Error ? e.message : 'Failed to create package';
		}
		newPkgSaving = false;
	}
</script>

{#snippet treeNode(node: DiagramHierarchyNode, depth: number)}
	{@const isPackage = node.node_type === 'package'}
	{@const isSelected = selectedId === node.id}
	{@const isExcluded = node.id === excludePackageId}
	{@const hasChildren = (node.children ?? []).length > 0}
	{@const isExpanded = expandedIds.has(node.id)}
	{@const visible = matchesSearch(node)}
	{#if visible}
		<li role="treeitem" aria-expanded={hasChildren ? isExpanded : undefined}>
			<div
				class="tree-row"
				class:tree-row--selected={isSelected}
				style="padding-left: {depth * 20 + 8}px"
			>
				{#if hasChildren}
					<button
						onclick={() => toggleExpand(node.id)}
						class="tree-toggle"
						aria-label={isExpanded ? 'Collapse' : 'Expand'}
					>
						<span aria-hidden="true">{isExpanded ? '▼' : '▶'}</span>
					</button>
				{:else}
					<span class="tree-spacer" aria-hidden="true"></span>
				{/if}
				<button
					onclick={() => selectNode(node)}
					class="tree-label"
					class:tree-label--package={isPackage}
					class:tree-label--diagram={!isPackage}
					class:tree-label--excluded={isExcluded}
					disabled={!isPackage || isExcluded}
					title={isPackage ? (isExcluded ? 'Cannot select this package' : 'Click to select') : 'Diagrams cannot be selected'}
				>
					<span class="tree-icon" aria-hidden="true">{isPackage ? '📁' : '📄'}</span>
					<span class="tree-name">{node.name}</span>
				</button>
			</div>
			{#if hasChildren && isExpanded}
				<ul role="group" class="tree-children">
					{#each node.children as child (child.id)}
						{@render treeNode(child, depth + 1)}
					{/each}
				</ul>
			{/if}
		</li>
	{/if}
{/snippet}

{#if open}
	<dialog
		bind:this={dialogEl}
		onkeydown={handleKeydown}
		aria-labelledby="package-picker-title"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border); min-width: 460px; max-height: 580px"
	>
		<h2 id="package-picker-title" class="text-lg font-bold">{title}</h2>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">{subtitle}</p>

		<div class="mt-3">
			<label for="package-picker-search" class="sr-only">Search hierarchy</label>
			<input
				id="package-picker-search"
				bind:value={search}
				type="search"
				placeholder="Search..."
				autocomplete="off"
				class="w-full rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			/>
		</div>

		<div class="mt-3" style="max-height: 280px; overflow-y: auto">
			{#if loading}
				<p class="text-sm" style="color: var(--color-muted)">Loading hierarchy...</p>
			{:else if hierarchy.length === 0}
				<p class="text-sm" style="color: var(--color-muted)">No packages found in this set.</p>
			{:else}
				<ul role="tree" class="tree-root" aria-label="Package hierarchy">
					{#each hierarchy as node (node.id)}
						{@render treeNode(node, 0)}
					{/each}
				</ul>
			{/if}
		</div>

		{#if selectedId}
			<p class="mt-2 text-xs" style="color: var(--color-primary)">
				Selected: <strong>{selectedName}</strong>
			</p>
		{/if}

		<!-- New package form -->
		{#if showNewForm}
			<div class="mt-3 rounded border p-3" style="border-color: var(--color-border)">
				<p class="mb-2 text-xs" style="color: var(--color-muted)">
					{selectedId ? `New child package under "${selectedName}"` : 'New package at set root'}
				</p>
				{#if newPkgError}
					<p class="mb-2 text-xs" style="color: var(--color-danger)">{newPkgError}</p>
				{/if}
				<div class="flex gap-2">
					<input
						type="text"
						bind:value={newPkgName}
						placeholder="Package name"
						class="flex-1 rounded border px-2 py-1 text-sm"
						style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						onkeydown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); createNewPackage(); } }}
					/>
					<button
						onclick={createNewPackage}
						disabled={!newPkgName.trim() || newPkgSaving}
						class="rounded px-3 py-1 text-sm text-white disabled:opacity-50"
						style="background-color: var(--color-primary)"
					>
						{newPkgSaving ? '...' : 'Create'}
					</button>
					<button
						onclick={() => { showNewForm = false; newPkgName = ''; newPkgError = null; }}
						class="rounded px-2 py-1 text-sm"
						style="border: 1px solid var(--color-border); color: var(--color-muted)"
					>
						Cancel
					</button>
				</div>
			</div>
		{/if}

		<div class="mt-4 flex items-center justify-between">
			<button
				type="button"
				onclick={() => { showNewForm = !showNewForm; newPkgName = ''; newPkgError = null; }}
				class="rounded px-3 py-2 text-sm"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				{showNewForm ? 'Hide' : 'New Package'}
			</button>
			<div class="flex gap-2">
				<button
					type="button"
					onclick={oncancel}
					class="rounded px-4 py-2 text-sm"
					style="border: 1px solid var(--color-border); color: var(--color-fg)"
				>
					Cancel
				</button>
				<button
					type="button"
					onclick={confirmSelection}
					disabled={!selectedId}
					class="rounded px-4 py-2 text-sm text-white disabled:opacity-50"
					style="background-color: var(--color-primary)"
				>
					OK
				</button>
			</div>
		</div>
	</dialog>
{/if}

<style>
	.tree-root {
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.tree-children {
		list-style: none;
		padding: 0;
		margin: 0;
	}
	.tree-row {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 2px 8px;
		border-radius: 4px;
	}
	.tree-row:hover {
		background-color: var(--color-bg);
	}
	.tree-row--selected {
		background-color: var(--color-primary);
		color: white;
	}
	.tree-row--selected:hover {
		background-color: var(--color-primary);
	}
	.tree-toggle {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 18px;
		height: 18px;
		border: none;
		background: none;
		cursor: pointer;
		font-size: 10px;
		color: var(--color-muted);
		flex-shrink: 0;
	}
	.tree-row--selected .tree-toggle {
		color: white;
	}
	.tree-spacer {
		width: 18px;
		flex-shrink: 0;
	}
	.tree-label {
		display: flex;
		align-items: center;
		gap: 6px;
		border: none;
		background: none;
		cursor: pointer;
		font-size: 0.875rem;
		color: inherit;
		flex: 1;
		min-width: 0;
		padding: 2px 0;
		text-align: left;
	}
	.tree-label--diagram {
		cursor: default;
		opacity: 0.5;
	}
	.tree-label--excluded {
		cursor: not-allowed;
		opacity: 0.3;
	}
	.tree-icon {
		font-size: 0.75rem;
		flex-shrink: 0;
	}
	.tree-name {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
</style>
