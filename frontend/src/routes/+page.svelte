<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import { setActiveSet, clearActiveSet, getActiveSetId } from '$lib/stores/activeSet.svelte.js';
	import { setActiveCollection, clearActiveCollection, getActiveCollectionId } from '$lib/stores/activeCollection.svelte.js';
	import TreeNode from '$lib/components/TreeNode.svelte';
	import DiagramDialog from '$lib/components/DiagramDialog.svelte';
	import Pagination from '$lib/components/Pagination.svelte';
	import KnowledgeGraph from '$lib/components/KnowledgeGraph.svelte';
	import KnowledgeGraphSettings from '$lib/components/KnowledgeGraphSettings.svelte';
	import { loadGraphSettings, saveGraphSettings } from '$lib/utils/graphColors';
	import { addAiContextItem, removeAiContextItem, getAiContextItems } from '$lib/stores/aiContext.svelte.js';
	import { getVisitHistory, clearVisitHistory, type VisitEntry } from '$lib/stores/visitHistory.svelte.js';
	import type {
		PaginatedResponse,
		Element,
		Diagram,
		SearchResult,
		SearchResponse,
		IrisSet,
		IrisCollection,
		DiagramHierarchyNode,
		GraphNode,
		GraphEdge,
		GraphResponse,
	} from '$lib/types/api';

	let elementCount = $state(0);
	let diagramCount = $state(0);
	let setCount = $state(0);
	let collectionCount = $state(0);
	let activeSet = $state<IrisSet | null>(null);
	let activeCollection = $state<IrisCollection | null>(null);
	let setCollectionNameMap = $state<Record<string, string>>({});
	let graphNodes = $state<GraphNode[]>([]);
	let graphEdges = $state<GraphEdge[]>([]);
	let graphLoading = $state(true);
	let graphScopeId = $derived(setId || collectionId || '');
	let graphSettings = $state(loadGraphSettings());

	// Reload settings when scope changes (set overrides collection)
	$effect(() => {
		void setId;
		void collectionId;
		graphSettings = loadGraphSettings(setId || undefined, collectionId || undefined);
	});
	let showGraphSettings = $state(false);
	let searchQuery = $state('');
	let searchResults = $state<SearchResult[]>([]);
	let searching = $state(false);
	let searchTypeFilter = $state('');
	let searchPage = $state(1);
	let searchPageSize = $state(25);

	const _typeOrder = ['collection', 'set', 'package', 'diagram', 'element'];
	let searchTypeCounts = $derived.by(() => {
		const counts: Record<string, number> = {};
		for (const r of searchResults) {
			counts[r.result_type] = (counts[r.result_type] || 0) + 1;
		}
		return Object.fromEntries(
			_typeOrder.filter((t) => t in counts).map((t) => [t, counts[t]])
		);
	});

	let filteredSearchResults = $derived(
		searchTypeFilter ? searchResults.filter((r) => r.result_type === searchTypeFilter) : searchResults
	);
	let searchTotal = $derived(filteredSearchResults.length);
	let paginatedSearchResults = $derived(
		filteredSearchResults.slice((searchPage - 1) * searchPageSize, searchPage * searchPageSize)
	);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let hierarchyTree = $state<DiagramHierarchyNode[]>([]);
	let hierarchyLoading = $state(false);
	let autoExpandDepth = $state(2);
	let treeSearchQuery = $state('');
	let treeExpandedIds = $state(new Set<string>());
	let reorderMode = $state(false);
	let showCreateMenu = $state(false);
	let showCreateDiagramDialog = $state(false);
	let showCreatePackageDialog = $state(false);
	let newPackageName = $state('');
	let newPackageDescription = $state('');

	// Dashboard tabs
	let dashboardTab = $state<'discover' | 'history'>('discover');
	let viewTab = $state<'hierarchy' | 'graph'>('hierarchy');
	let wideEnough = $state(false);
	let hoveredNodeId = $state<string | null>(null);
	let graphHoveredNodeId = $state<string | null>(null);

	// Find the ancestor path to a node in the hierarchy tree.
	function findAncestorPath(trees: DiagramHierarchyNode[], targetId: string): string[] {
		for (const node of trees) {
			if (node.id === targetId) return [node.id];
			if (node.children?.length) {
				const path = findAncestorPath(node.children, targetId);
				if (path.length) return [node.id, ...path];
			}
		}
		return [];
	}

	// Peek: temporarily expand ancestors to reveal hovered graph node.
	// If expanding would push the tree beyond the viewport (i.e. the target
	// is deeper than autoExpandDepth), don't expand — just highlight the
	// deepest already-visible ancestor instead.
	let graphHoverIds = $derived.by(() => {
		if (!graphHoveredNodeId || !hierarchyTree.length) return new Set<string>();
		const path = findAncestorPath(hierarchyTree, graphHoveredNodeId);
		if (!path.length) return new Set<string>();
		// If the target is already visible (within auto-expand depth), highlight it directly
		if (path.length - 1 <= autoExpandDepth) return new Set([graphHoveredNodeId]);
		// Otherwise highlight the deepest visible ancestor
		const deepestVisible = path[Math.max(autoExpandDepth, 0)];
		return new Set([deepestVisible]);
	});

	let peekExpandedIds = $derived.by(() => {
		if (!graphHoveredNodeId || !hierarchyTree.length) return new Set<string>();
		const path = findAncestorPath(hierarchyTree, graphHoveredNodeId);
		if (!path.length) return new Set<string>();
		// Only peek-expand if the target is within reach (won't cause overflow)
		if (path.length - 1 <= autoExpandDepth) {
			return new Set(path.slice(0, -1));
		}
		// Too deep — don't expand anything
		return new Set<string>();
	});

	// History tab
	let historySearchQuery = $state('');
	let visitHistory = $derived(getVisitHistory());
	let filteredHistory = $derived.by(() => {
		let results = historySearchQuery.trim()
			? visitHistory.filter((e) => e.name.toLowerCase().includes(historySearchQuery.trim().toLowerCase()) || e.type.includes(historySearchQuery.trim().toLowerCase()))
			: visitHistory;
		// Enrich with collection names from the loaded sets map
		if (Object.keys(setCollectionNameMap).length > 0) {
			results = results.map((e) => {
				if (!e.collectionName && e.setId && setCollectionNameMap[e.setId]) {
					return { ...e, collectionName: setCollectionNameMap[e.setId] };
				}
				return e;
			});
		}
		return results;
	});
	let groupedHistory = $derived.by(() => {
		const groups: Record<string, VisitEntry[]> = {};
		const today = new Date(); today.setHours(0, 0, 0, 0);
		const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1);
		const weekAgo = new Date(today); weekAgo.setDate(weekAgo.getDate() - 7);
		for (const entry of filteredHistory) {
			const d = new Date(entry.visitedAt); d.setHours(0, 0, 0, 0);
			let label: string;
			if (d.getTime() === today.getTime()) label = 'Today';
			else if (d.getTime() === yesterday.getTime()) label = 'Yesterday';
			else if (d >= weekAgo) label = 'This week';
			else label = d.toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' });
			(groups[label] ??= []).push(entry);
		}
		return groups;
	});

	// Reactive to URL param changes so clicking a set/collection in the graph updates the view
	let setId = $derived(page.url.searchParams.get('set_id') || getActiveSetId() || '');
	let collectionId = $derived(page.url.searchParams.get('collection_id') || getActiveCollectionId() || '');

	$effect(() => {
		// Re-run when scope changes
		void setId;
		void collectionId;
		loadDashboard();
	});

	// Responsive: side-by-side when wide enough
	$effect(() => {
		const mql = window.matchMedia('(min-width: 1024px)');
		wideEnough = mql.matches;
		const handler = (e: MediaQueryListEvent) => { wideEnough = e.matches; };
		mql.addEventListener('change', handler);
		return () => mql.removeEventListener('change', handler);
	});

	async function loadDashboard() {
		loading = true;
		error = null;
		try {
			const setFilter = setId ? `&set_id=${setId}` : '';
			const collectionFilter = !setId && collectionId ? `&collection_id=${collectionId}` : '';

			const setsFilter = collectionId ? `?collection_id=${collectionId}` : '';
			const [elementsData, diagramsData, setsData, collectionsData] = await Promise.all([
				apiFetch<PaginatedResponse<Element>>(`/api/elements?page_size=1${setFilter}${collectionFilter}`),
				apiFetch<PaginatedResponse<Element>>(`/api/diagrams?page_size=1${setFilter}${collectionFilter}`),
				apiFetch<{ items: IrisSet[] }>(`/api/sets${setsFilter}`),
				apiFetch<{ items: IrisCollection[] }>('/api/collections'),
			]);
			elementCount = elementsData.total;
			diagramCount = diagramsData.total;
			setCount = setsData.items.length;
			collectionCount = collectionsData.items.length;

			// Build set → collection name map for history tab
			const nameMap: Record<string, string> = {};
			for (const s of setsData.items) {
				if (s.collection_id && s.collection_name) nameMap[s.id] = s.collection_name;
			}
			setCollectionNameMap = nameMap;

			// Resolve active set/collection for display
			const hasUrlSetId = !!page.url.searchParams.get('set_id');
			const hasUrlCollectionId = !!page.url.searchParams.get('collection_id');
			if (setId) {
				activeSet = setsData.items.find((s) => s.id === setId) ?? null;
				if (activeSet && hasUrlSetId) {
					setActiveSet(activeSet.id, activeSet.name);
				} else if (!activeSet && hasUrlSetId) {
					// Invalid set_id in URL — clear it
					clearActiveSet();
					goto('/', { replaceState: true });
					return;
				}
			} else {
				activeSet = null;
			}

			if (collectionId && !setId) {
				activeCollection = collectionsData.items.find((c) => c.id === collectionId) ?? null;
				if (activeCollection && hasUrlCollectionId) {
					setActiveCollection(activeCollection.id, activeCollection.name);
				} else if (!activeCollection && hasUrlCollectionId) {
					// Invalid collection_id in URL — clear it
					clearActiveCollection();
					goto('/', { replaceState: true });
					return;
				}
			} else if (activeSet?.collection_id) {
				activeCollection = collectionsData.items.find((c) => c.id === activeSet!.collection_id) ?? null;
			} else {
				activeCollection = null;
			}
		} catch {
			error = 'Failed to load dashboard data';
		}
		loading = false;

		if (setId) {
			loadHierarchy();
		} else {
			hierarchyTree = [];
		}

		loadGraph();
	}

	// Count visible nodes at a given auto-expand depth
	function countVisibleNodes(trees: DiagramHierarchyNode[], depth: number, maxDepth: number): number {
		let count = trees.length;
		if (depth < maxDepth) {
			for (const node of trees) {
				if (node.children?.length) {
					count += countVisibleNodes(node.children, depth + 1, maxDepth);
				}
			}
		}
		return count;
	}

	function calcAutoExpandDepth(trees: DiagramHierarchyNode[]): number {
		// ~30px per row, reserve ~300px for stats/search/tabs above the tree
		const availableHeight = (typeof window !== 'undefined' ? window.innerHeight : 800) - 300;
		const rowHeight = 30;
		const maxRows = Math.floor(availableHeight / rowHeight);

		// Try increasing depth until too many nodes
		for (let d = 0; d <= 6; d++) {
			const count = countVisibleNodes(trees, 0, d);
			if (count > maxRows) return Math.max(d - 1, 0);
		}
		return 6;
	}

	async function loadHierarchy() {
		hierarchyLoading = true;
		try {
			hierarchyTree = await apiFetch<DiagramHierarchyNode[]>(
				`/api/diagrams/hierarchy?set_id=${setId}`
			);
			autoExpandDepth = calcAutoExpandDepth(hierarchyTree);
		} catch {
			hierarchyTree = [];
		}
		hierarchyLoading = false;
	}

	async function loadGraph() {
		graphLoading = true;
		try {
			const params = setId ? `set_id=${setId}` : collectionId ? `collection_id=${collectionId}` : '';
			const url = params ? `/api/graph?${params}` : '/api/graph';
			const data = await apiFetch<GraphResponse>(url);
			graphNodes = data.nodes;
			graphEdges = data.edges;
		} catch {
			graphNodes = [];
			graphEdges = [];
		}
		graphLoading = false;
	}

	async function handleReorder(parentId: string | null, orderedIds: string[]) {
		try {
			await apiFetch('/api/diagrams/reorder', {
				method: 'PUT',
				body: JSON.stringify({
					parent_package_id: parentId,
					ordered_ids: orderedIds,
				}),
			});
			await loadHierarchy();
		} catch {
			// Reload to reset to server state
			await loadHierarchy();
		}
	}

	async function handleCreateDiagram(name: string, diagramType: string, description: string, _tags?: string[], _isTemplate?: boolean, notation?: string) {
		try {
			const body: Record<string, unknown> = { diagram_type: diagramType, name, description, data: {} };
			if (setId) body.set_id = setId;
			if (notation) body.notation = notation;
			const created = await apiFetch<Diagram>('/api/diagrams', {
				method: 'POST',
				body: JSON.stringify(body),
			});
			showCreateDiagramDialog = false;
			await loadHierarchy();
			await goto(`/diagrams/${created.id}`);
		} catch {
			// handled by dialog
		}
	}

	async function handleCreatePackage() {
		if (!newPackageName.trim()) return;
		try {
			const created = await apiFetch<{ id: string }>('/api/packages', {
				method: 'POST',
				body: JSON.stringify({
					name: newPackageName.trim(),
					description: newPackageDescription.trim() || null,
					set_id: setId || undefined,
				}),
			});
			showCreatePackageDialog = false;
			newPackageName = '';
			newPackageDescription = '';
			await loadHierarchy();
			await goto(`/packages/${created.id}`);
		} catch {
			// handled
		}
	}

	async function handleSearch() {
		const q = searchQuery.trim();
		if (!q) {
			searchResults = [];
			return;
		}
		searching = true;
		searchTypeFilter = '';
		searchPage = 1;
		try {
			const setFilter = setId ? `&set_id=${setId}` : '';
			const collectionFilter = !setId && collectionId ? `&collection_id=${collectionId}` : '';
			const data = await apiFetch<SearchResponse>(`/api/search?q=${encodeURIComponent(q)}&limit=200${setFilter}${collectionFilter}`);
			searchResults = data.results;
		} catch {
			searchResults = [];
		}
		searching = false;
	}

	let contextItems = $derived(getAiContextItems());
	let contextItemIds = $derived(new Set(contextItems.map((i) => i.id)));

	function handleAddToContext(result: SearchResult) {
		addAiContextItem({
			id: result.id,
			result_type: result.result_type,
			name: result.name,
			set_id: result.set_id,
			set_name: result.set_name,
		});
	}

	function handleTreeAddToContext(node: DiagramHierarchyNode) {
		addAiContextItem({
			id: node.id,
			result_type: node.node_type === 'package' ? 'package' : 'diagram',
			name: node.name,
			set_id: setId || null,
			set_name: activeSet?.name ?? null,
		});
	}

	function handleResultClick(result: SearchResult) {
		searchQuery = '';
		searchResults = [];
		if (result.result_type === 'collection') {
			setActiveCollection(result.id, result.name);
			goto(`/?collection_id=${result.id}`);
		} else if (result.result_type === 'set') {
			setActiveSet(result.id, result.name);
			if (result.collection_name) {
				// Collection info not available as ID from search — navigate and let dashboard resolve
			} else {
				clearActiveCollection();
			}
			goto(`/?set_id=${result.id}`);
		}
	}

	let searchTimeout: ReturnType<typeof setTimeout> | undefined;
	function onSearchInput() {
		clearTimeout(searchTimeout);
		searchTimeout = setTimeout(handleSearch, 300);
	}
</script>

<svelte:head>
	<title>Dashboard — Iris</title>
</svelte:head>

<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Dashboard</h1>
<p class="mt-1 text-sm" style="color: var(--color-muted)">Integrated Repository for Information & Systems</p>

<!-- Dashboard tabs -->
<div class="mt-3 flex gap-0 border-b" style="border-color: var(--color-border)" role="tablist" aria-label="Dashboard sections">
	<button
		role="tab"
		aria-selected={dashboardTab === 'discover'}
		onclick={() => (dashboardTab = 'discover')}
		class="px-5 py-2 text-sm font-medium transition-colors"
		style="color: {dashboardTab === 'discover' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {dashboardTab === 'discover' ? 'var(--color-primary)' : 'transparent'}; margin-bottom: -1px"
	>
		Discover
	</button>
	<button
		role="tab"
		aria-selected={dashboardTab === 'history'}
		onclick={() => (dashboardTab = 'history')}
		class="px-5 py-2 text-sm font-medium transition-colors"
		style="color: {dashboardTab === 'history' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {dashboardTab === 'history' ? 'var(--color-primary)' : 'transparent'}; margin-bottom: -1px"
	>
		History
	</button>
</div>

{#if dashboardTab === 'discover'}
{#if loading}
	<p class="mt-4" style="color: var(--color-muted)">Loading dashboard...</p>
{:else if error}
	<div role="alert" class="mt-4" style="color: var(--color-danger)">{error}</div>
{:else}

	{#if (setId || collectionId) && !activeSet && !activeCollection}
		<div class="mt-4">
			<button
				onclick={() => { clearActiveSet(); clearActiveCollection(); setId = ''; collectionId = ''; loadDashboard(); }}
				class="rounded border px-3 py-1.5 text-sm"
				style="border-color: var(--color-border); color: var(--color-primary)"
			>
				Reset filters
			</button>
		</div>
	{/if}

	<!-- Stats -->
	<div class="mt-6 grid grid-cols-4 gap-4" style="max-width: 800px">
		<div
			class="rounded border p-4 text-center"
			style="border-color: var(--color-border); color: var(--color-fg)"
		>
			{#if activeCollection}
				<div class="text-xl font-bold" style="color: var(--color-fg)">{activeCollection.name}</div>
				<button
					onclick={() => { clearActiveCollection(); clearActiveSet(); setId = ''; collectionId = ''; loadDashboard(); }}
					class="mt-1 inline-block text-sm"
					style="color: var(--color-primary); background: none; border: none; cursor: pointer; padding: 0"
				>
					Reset filter
				</button>
			{:else}
				<a href="/collections" style="color: inherit; text-decoration: none">
					<div class="text-3xl font-bold" style="color: var(--color-primary)">{activeSet && !activeSet.collection_id ? '-' : collectionCount}</div>
					<div class="mt-1 text-sm" style="color: var(--color-muted)">Collections</div>
				</a>
			{/if}
		</div>
		<div
			class="rounded border p-4 text-center"
			style="border-color: var(--color-border); color: var(--color-fg)"
		>
			{#if activeSet}
				<div class="text-xl font-bold" style="color: var(--color-fg)">{activeSet.name}</div>
				<button
					onclick={() => { clearActiveSet(); setId = ''; loadDashboard(); }}
					class="mt-1 inline-block text-sm"
					style="color: var(--color-primary); background: none; border: none; cursor: pointer; padding: 0"
				>
					Reset filter
				</button>
			{:else}
				<a href={collectionId ? `/sets?collection_id=${collectionId}` : '/sets'} style="color: inherit; text-decoration: none">
					<div class="text-3xl font-bold" style="color: var(--color-primary)">{setCount}</div>
					<div class="mt-1 text-sm" style="color: var(--color-muted)">Sets {#if activeCollection}(filtered){/if}</div>
				</a>
			{/if}
		</div>
		<a
			href={setId ? `/diagrams?set_id=${setId}` : collectionId ? `/diagrams?collection_id=${collectionId}` : '/diagrams'}
			class="rounded border p-4 text-center"
			style="border-color: var(--color-border); color: var(--color-fg)"
		>
			<div class="text-3xl font-bold" style="color: var(--color-primary)">{diagramCount}</div>
			<div class="mt-1 text-sm" style="color: var(--color-muted)">
				Diagrams {#if activeSet || activeCollection}(filtered){/if}
			</div>
		</a>
		<a
			href={setId ? `/elements?set_id=${setId}` : collectionId ? `/elements?collection_id=${collectionId}` : '/elements'}
			class="rounded border p-4 text-center"
			style="border-color: var(--color-border); color: var(--color-fg)"
		>
			<div class="text-3xl font-bold" style="color: var(--color-primary)">{elementCount}</div>
			<div class="mt-1 text-sm" style="color: var(--color-muted)">
				Elements {#if activeSet || activeCollection}(filtered){/if}
			</div>
		</a>
	</div>

	<p class="mt-4 text-sm" style="color: var(--color-muted)">
		Filter by Collection or Set above, or search across your architecture repository below.
	</p>

	<!-- Diagram Hierarchy + Knowledge Graph -->
	{#if true}
		{@const hasHierarchy = !!activeSet}
		{@const showSideBySide = hasHierarchy && wideEnough}

		<div class="mt-4 flex flex-1 flex-col" style="min-height: 0">
			<!-- Tabs (narrow mode with hierarchy, or collection-only = graph only) -->
			{#if hasHierarchy && !showSideBySide}
				<div class="flex gap-0 border-b" style="border-color: var(--color-border)" role="tablist" aria-label="Set view">
					<button
						role="tab"
						aria-selected={viewTab === 'hierarchy'}
						onclick={() => (viewTab = 'hierarchy')}
						class="px-5 py-2 text-sm font-medium transition-colors"
						style="color: {viewTab === 'hierarchy' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {viewTab === 'hierarchy' ? 'var(--color-primary)' : 'transparent'}; margin-bottom: -1px"
					>
						Diagram Hierarchy
					</button>
					<button
						role="tab"
						aria-selected={viewTab === 'graph'}
						onclick={() => (viewTab = 'graph')}
						class="px-5 py-2 text-sm font-medium transition-colors"
						style="color: {viewTab === 'graph' ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {viewTab === 'graph' ? 'var(--color-primary)' : 'transparent'}; margin-bottom: -1px"
					>
						Knowledge Graph
					</button>
				</div>
			{/if}

			<!-- Content -->
			<div class="mt-4 flex flex-1 gap-4" style="min-height: 0">
				<!-- Hierarchy panel -->
				{#if hasHierarchy && (showSideBySide || viewTab === 'hierarchy')}
					<div style="max-width: 500px; min-width: 280px; {showSideBySide ? 'flex: 0 0 380px;' : 'width: 100%;'} overflow-y: auto">
						<div class="flex items-center gap-1" style="position: relative">
							<button
								onclick={() => { showCreateMenu = !showCreateMenu; }}
								class="rounded px-2 py-1 text-xs"
								style="background: var(--color-primary); color: white"
								title="Create new item"
							>+ New</button>
							{#if showCreateMenu}
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<div style="position: fixed; inset: 0; z-index: 9" onclick={() => (showCreateMenu = false)}></div>
								<div style="position: absolute; top: 100%; left: 0; z-index: 10; margin-top: 4px; min-width: 120px; border-radius: 6px; border: 1px solid var(--color-border); background: var(--color-surface); box-shadow: 0 4px 12px rgba(0,0,0,0.15); overflow: hidden">
									<button onclick={() => { showCreateDiagramDialog = true; showCreateMenu = false; }} class="block w-full px-3 py-2 text-left text-xs" style="color: var(--color-fg); background: none; border: none; cursor: pointer">Diagram</button>
									<button onclick={() => { showCreatePackageDialog = true; showCreateMenu = false; }} class="block w-full px-3 py-2 text-left text-xs" style="color: var(--color-fg); background: none; border: none; border-top: 1px solid var(--color-border); cursor: pointer">Package</button>
								</div>
							{/if}
							<button
								onclick={() => { reorderMode = !reorderMode; }}
								class="rounded px-2 py-1 text-xs"
								style="border: 1px solid {reorderMode ? 'var(--color-primary)' : 'var(--color-border)'}; background: {reorderMode ? 'var(--color-primary)' : 'transparent'}; color: {reorderMode ? 'white' : 'var(--color-muted)'}"
								title={reorderMode ? 'Exit reorder mode' : 'Reorder diagrams'}
							>
								{reorderMode ? 'Done' : 'Reorder'}
							</button>
						</div>
						<input
							id="tree-search"
							bind:value={treeSearchQuery}
							type="search"
							placeholder="Filter diagrams..."
							class="mt-2 w-full rounded border px-3 py-2 text-sm"
							style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
						/>
						{#if hierarchyLoading}
							<p class="mt-2 text-sm" style="color: var(--color-muted)">Loading hierarchy...</p>
						{:else if hierarchyTree.length === 0}
							<p class="mt-2 text-sm" style="color: var(--color-muted)">No diagrams in this set.</p>
						{:else}
							<ul role="tree" class="mt-4" style="list-style: none; padding: 0; margin: 0">
								{#each hierarchyTree as node (node.id)}
									<TreeNode {node} searchQuery={treeSearchQuery} expandedIds={treeExpandedIds} siblings={hierarchyTree} onreorder={reorderMode ? handleReorder : undefined} {contextItemIds} onaddcontext={handleTreeAddToContext} onremovecontext={removeAiContextItem} onhover={(id) => { hoveredNodeId = id; }} {graphHoverIds} {peekExpandedIds} {autoExpandDepth} />
								{/each}
							</ul>
						{/if}
					</div>
				{/if}

				<!-- Graph panel -->
				{#if showSideBySide || viewTab === 'graph' || !hasHierarchy}
					<div class="flex flex-1 flex-col" style="min-height: 0; min-width: 0">
						<div class="mb-2 flex items-center justify-end" style="position: relative">
							<button
								onclick={() => { showGraphSettings = !showGraphSettings; }}
								class="rounded p-1"
								style="color: var(--color-muted); background: none; border: none; cursor: pointer"
								title="Graph settings"
							>
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="16" height="16">
									<path d="M40,88H73a32,32,0,0,0,62,0h81a8,8,0,0,0,0-16H135a32,32,0,0,0-62,0H40a8,8,0,0,0,0,16Zm64-24a16,16,0,1,1-16,16A16,16,0,0,1,104,64ZM216,168H199a32,32,0,0,0-62,0H40a8,8,0,0,0,0,16h97a32,32,0,0,0,62,0h17a8,8,0,0,0,0-16Zm-48,24a16,16,0,1,1,16-16A16,16,0,0,1,168,192Z"/>
								</svg>
							</button>
							{#if showGraphSettings}
								<!-- svelte-ignore a11y_no_static_element_interactions -->
								<div style="position: fixed; inset: 0; z-index: 19" onclick={() => (showGraphSettings = false)}></div>
								<KnowledgeGraphSettings
									settings={graphSettings}
									onchange={(s) => { graphSettings = s; saveGraphSettings(s, graphScopeId); }}
								/>
							{/if}
						</div>
						{#if graphLoading}
							<p class="text-sm" style="color: var(--color-muted)">Loading graph...</p>
						{:else if graphNodes.length === 0}
							<p class="text-sm" style="color: var(--color-muted)">No elements yet.</p>
						{:else}
							<KnowledgeGraph
								nodes={graphNodes}
								edges={graphEdges}
								settings={graphSettings}
								onNodeClick={(nodeId, nodeType) => {
									if (nodeType === 'collection') {
										goto(`/?collection_id=${nodeId}`);
									} else if (nodeType === 'set') {
										goto(`/?set_id=${nodeId}`);
									} else {
										const routeMap: Record<string, string> = { package: '/packages', diagram: '/diagrams', element: '/elements' };
										goto(`${routeMap[nodeType] || '/elements'}/${nodeId}`);
									}
								}}
								highlightNodeId={hoveredNodeId}
								onNodeHover={(id) => { graphHoveredNodeId = id; }}
							/>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Search -->
	<div class="mt-6">
		<label for="dashboard-search" class="text-sm font-medium" style="color: var(--color-fg)">Search</label>
		<input
			id="dashboard-search"
			bind:value={searchQuery}
			oninput={onSearchInput}
			type="search"
			placeholder="Search elements and diagrams..."
			class="mt-1 w-full rounded border px-3 py-2 text-sm"
			style="max-width: 500px; border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		/>
	</div>

	{#if searching}
		<p class="mt-2 text-sm" style="color: var(--color-muted)">Searching...</p>
	{:else if searchResults.length > 0}
		<div class="mt-3" aria-live="polite">
			<p class="mb-2 text-sm" style="color: var(--color-muted)">{searchResults.length} result{searchResults.length === 1 ? '' : 's'}</p>
			<div class="mb-2 flex flex-wrap items-center gap-2" style="max-width: 800px">
				{#each Object.entries(searchTypeCounts) as [type, count]}
					<button
						onclick={() => { searchTypeFilter = searchTypeFilter === type ? '' : type; searchPage = 1; }}
						class="rounded px-2 py-0.5 text-xs"
						style="background: {searchTypeFilter === type ? 'var(--color-primary)' : 'var(--color-surface)'}; color: {searchTypeFilter === type ? 'white' : 'var(--color-muted)'}; cursor: pointer"
					>
						{type} ({count})
					</button>
				{/each}
				{#if searchTypeFilter}
					<button
						onclick={() => { searchTypeFilter = ''; searchPage = 1; }}
						class="text-xs underline"
						style="color: var(--color-muted)"
					>
						reset
					</button>
				{/if}
			</div>
			<ul class="flex flex-col gap-2" style="max-width: 800px">
				{#each paginatedSearchResults as result}
					<li>
						<div
							class="rounded border p-3"
							style="border-color: var(--color-border); color: var(--color-fg)"
						>
							{#if result.result_type === 'collection' || result.result_type === 'set'}
								<button
									onclick={() => handleResultClick(result)}
									class="block w-full text-left"
									style="color: inherit; background: none; border: none; cursor: pointer; padding: 0"
								>
									<div class="flex flex-wrap items-center gap-2">
										<span class="text-sm font-medium" style="color: var(--color-primary)">{result.name}</span>
										<span class="rounded border px-2 py-0.5 text-xs" style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-fg)">
											{result.result_type}
										</span>
										{#if result.collection_name && result.result_type === 'set'}
											<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
												{result.collection_name}
											</span>
										{/if}
									</div>
									{#if result.description}
										<div class="mt-1 text-xs" style="color: var(--color-muted)">{result.description}</div>
									{/if}
								</button>
							{:else}
								<a
									href={result.deep_link}
									class="block"
									style="color: inherit"
								>
									<div class="flex flex-wrap items-center gap-2">
										<span class="text-sm font-medium" style="color: var(--color-primary)">{result.name}</span>
										<span class="rounded border px-2 py-0.5 text-xs" style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-fg)">
											{result.result_type} · {result.type_detail}
										</span>
										{#if result.collection_name}
											<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
												{result.collection_name}
											</span>
										{/if}
										{#if result.set_name}
											<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
												{result.set_name}
											</span>
										{/if}
									</div>
									{#if result.package_name}
										<div class="mt-1 text-xs" style="color: var(--color-muted)">
											{result.package_name}
										</div>
									{/if}
								</a>
							{/if}
							{#if result.result_type !== 'element'}
								<div class="mt-2 flex justify-end">
									{#if contextItemIds.has(result.id)}
										<button
											onclick={(e) => { e.preventDefault(); e.stopPropagation(); removeAiContextItem(result.id); }}
											class="added-context-btn rounded border px-2 py-1 text-xs"
											style="border-color: var(--color-primary); background: var(--color-primary); color: white; cursor: pointer; display: flex; align-items: center; gap: 4px"
											title="Remove from AI context"
										>
											<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="12" height="12" aria-hidden="true">
												<path d="M248,124a56.11,56.11,0,0,0-32-50.61V72a48,48,0,0,0-88-26.49A48,48,0,0,0,40,72v1.39a56,56,0,0,0,0,101.2V176a48,48,0,0,0,88,26.49A48,48,0,0,0,216,176v-1.41A56.09,56.09,0,0,0,248,124ZM88,208a32,32,0,0,1-31.81-28.56A55.87,55.87,0,0,0,64,180h8a8,8,0,0,0,0-16H64A40,40,0,0,1,50.67,86.27,8,8,0,0,0,56,78.73V72a32,32,0,0,1,64,0v68.26A47.8,47.8,0,0,0,88,128a8,8,0,0,0,0,16,32,32,0,0,1,0,64Zm104-44h-8a8,8,0,0,0,0,16h8a55.87,55.87,0,0,0,7.81-.56A32,32,0,1,1,168,144a8,8,0,0,0,0-16,47.8,47.8,0,0,0-32,12.26V72a32,32,0,0,1,64,0v6.73a8,8,0,0,0,5.33,7.54A40,40,0,0,1,192,164Zm16-52a8,8,0,0,1-8,8h-4a36,36,0,0,1-36-36V80a8,8,0,0,1,16,0v4a20,20,0,0,0,20,20h4A8,8,0,0,1,208,112ZM60,120H56a8,8,0,0,1,0-16h4A20,20,0,0,0,80,84V80a8,8,0,0,1,16,0v4A36,36,0,0,1,60,120Z"/>
											</svg>
											In context
										</button>
									{:else}
										<button
											onclick={(e) => { e.preventDefault(); e.stopPropagation(); handleAddToContext(result); }}
											class="add-context-btn rounded border py-1 text-xs"
											style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-primary); cursor: pointer"
											title="Add to Iris AI context"
										>
											<span class="add-context-inner">
												<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="12" height="12" aria-hidden="true" style="flex-shrink: 0">
													<path d="M248,124a56.11,56.11,0,0,0-32-50.61V72a48,48,0,0,0-88-26.49A48,48,0,0,0,40,72v1.39a56,56,0,0,0,0,101.2V176a48,48,0,0,0,88,26.49A48,48,0,0,0,216,176v-1.41A56.09,56.09,0,0,0,248,124ZM88,208a32,32,0,0,1-31.81-28.56A55.87,55.87,0,0,0,64,180h8a8,8,0,0,0,0-16H64A40,40,0,0,1,50.67,86.27,8,8,0,0,0,56,78.73V72a32,32,0,0,1,64,0v68.26A47.8,47.8,0,0,0,88,128a8,8,0,0,0,0,16,32,32,0,0,1,0,64Zm104-44h-8a8,8,0,0,0,0,16h8a55.87,55.87,0,0,0,7.81-.56A32,32,0,1,1,168,144a8,8,0,0,0,0-16,47.8,47.8,0,0,0-32,12.26V72a32,32,0,0,1,64,0v6.73a8,8,0,0,0,5.33,7.54A40,40,0,0,1,192,164Zm16-52a8,8,0,0,1-8,8h-4a36,36,0,0,1-36-36V80a8,8,0,0,1,16,0v4a20,20,0,0,0,20,20h4A8,8,0,0,1,208,112ZM60,120H56a8,8,0,0,1,0-16h4A20,20,0,0,0,80,84V80a8,8,0,0,1,16,0v4A36,36,0,0,1,60,120Z"/>
												</svg>
												<span class="add-context-plus">+</span>
												<span class="add-context-label">Add to context</span>
											</span>
										</button>
									{/if}
								</div>
							{/if}
						</div>
					</li>
				{/each}
			</ul>
			{#if searchTotal > searchPageSize}
				<div style="max-width: 800px">
					<Pagination
						page={searchPage}
						pageSize={searchPageSize}
						total={searchTotal}
						onpagechange={(p) => { searchPage = p; }}
						onpagesizechange={(s) => { searchPageSize = s; searchPage = 1; }}
					/>
				</div>
			{/if}
		</div>
	{:else if searchQuery.trim()}
		<p class="mt-2 text-sm" style="color: var(--color-muted)">No results found.</p>
	{/if}


{/if}
{:else}
	<!-- History tab -->
	<div class="mt-4">
		<div class="flex items-center gap-4">
			<input
				type="search"
				bind:value={historySearchQuery}
				placeholder="Search history..."
				class="rounded border px-3 py-2 text-sm"
				style="max-width: 500px; width: 100%; border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
			/>
			{#if visitHistory.length > 0}
				<button
					onclick={clearVisitHistory}
					class="text-xs"
					style="color: var(--color-muted)"
				>
					Clear history
				</button>
			{/if}
		</div>

		{#if filteredHistory.length === 0}
			<p class="mt-4 text-sm" style="color: var(--color-muted)">
				{historySearchQuery.trim() ? 'No history matches your search.' : 'No pages visited yet. Browse collections, sets, diagrams, packages, or elements to build your history.'}
			</p>
		{:else}
			{#each Object.entries(groupedHistory) as [dateLabel, items]}
				<h3 class="mt-5 mb-2 text-sm font-semibold" style="color: var(--color-muted)">{dateLabel}</h3>
				<ul class="flex flex-col gap-2" style="max-width: 800px">
					{#each items as entry}
						<li>
							<div
								class="rounded border p-3"
								style="border-color: var(--color-border); color: var(--color-fg)"
							>
								{#if entry.type === 'collection' || entry.type === 'set'}
									<button
										onclick={() => {
											if (entry.type === 'collection') {
												setActiveCollection(entry.id, entry.name);
												goto(`/?collection_id=${entry.id}`);
											} else {
												setActiveSet(entry.id, entry.name);
												goto(`/?set_id=${entry.id}`);
											}
										}}
										class="block w-full text-left"
										style="color: inherit; background: none; border: none; cursor: pointer; padding: 0"
									>
										<div class="flex flex-wrap items-center gap-2">
											<span class="text-sm font-medium" style="color: var(--color-primary)">{entry.name}</span>
											<span class="rounded border px-2 py-0.5 text-xs" style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-fg)">
												{entry.type}
											</span>
											{#if entry.collectionName && entry.type === 'set'}
												<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
													{entry.collectionName}
												</span>
											{/if}
										</div>
										{#if entry.description}
											<div class="mt-1 text-xs" style="color: var(--color-muted)">{entry.description}</div>
										{/if}
									</button>
								{:else}
									<a
										href={entry.href}
										class="block"
										style="color: inherit"
									>
										<div class="flex flex-wrap items-center gap-2">
											<span class="text-sm font-medium" style="color: var(--color-primary)">{entry.name}</span>
											<span class="rounded border px-2 py-0.5 text-xs" style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-fg)">
												{entry.type}{entry.detail ? ` · ${entry.detail}` : ''}
											</span>
											{#if entry.collectionName}
												<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
													{entry.collectionName}
												</span>
											{/if}
											{#if entry.setName}
												<span class="rounded px-2 py-0.5 text-xs" style="background: var(--color-surface); color: var(--color-muted)">
													{entry.setName}
												</span>
											{/if}
										</div>
										{#if entry.packageName}
											<div class="mt-1 text-xs" style="color: var(--color-muted)">
												{entry.packageName}
											</div>
										{/if}
									</a>
								{/if}
								{#if entry.type !== 'element'}
									<div class="mt-2 flex justify-end">
										{#if contextItemIds.has(entry.id)}
											<button
												onclick={(e) => { e.preventDefault(); e.stopPropagation(); removeAiContextItem(entry.id); }}
												class="added-context-btn rounded border px-2 py-1 text-xs"
												style="border-color: var(--color-primary); background: var(--color-primary); color: white; cursor: pointer; display: flex; align-items: center; gap: 4px"
												title="Remove from AI context"
											>
												<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="12" height="12" aria-hidden="true">
													<path d="M248,124a56.11,56.11,0,0,0-32-50.61V72a48,48,0,0,0-88-26.49A48,48,0,0,0,40,72v1.39a56,56,0,0,0,0,101.2V176a48,48,0,0,0,88,26.49A48,48,0,0,0,216,176v-1.41A56.09,56.09,0,0,0,248,124ZM88,208a32,32,0,0,1-31.81-28.56A55.87,55.87,0,0,0,64,180h8a8,8,0,0,0,0-16H64A40,40,0,0,1,50.67,86.27,8,8,0,0,0,56,78.73V72a32,32,0,0,1,64,0v68.26A47.8,47.8,0,0,0,88,128a8,8,0,0,0,0,16,32,32,0,0,1,0,64Zm104-44h-8a8,8,0,0,0,0,16h8a55.87,55.87,0,0,0,7.81-.56A32,32,0,1,1,168,144a8,8,0,0,0,0-16,47.8,47.8,0,0,0-32,12.26V72a32,32,0,0,1,64,0v6.73a8,8,0,0,0,5.33,7.54A40,40,0,0,1,192,164Zm16-52a8,8,0,0,1-8,8h-4a36,36,0,0,1-36-36V80a8,8,0,0,1,16,0v4a20,20,0,0,0,20,20h4A8,8,0,0,1,208,112ZM60,120H56a8,8,0,0,1,0-16h4A20,20,0,0,0,80,84V80a8,8,0,0,1,16,0v4A36,36,0,0,1,60,120Z"/>
												</svg>
												In context
											</button>
										{:else}
											<button
												onclick={(e) => { e.preventDefault(); e.stopPropagation(); addAiContextItem({ id: entry.id, result_type: entry.type, name: entry.name, set_id: entry.setId ?? null, set_name: entry.setName ?? null }); }}
												class="add-context-btn rounded border py-1 text-xs"
												style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-primary); cursor: pointer"
												title="Add to Iris AI context"
											>
												<span class="add-context-inner">
													<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="12" height="12" aria-hidden="true" style="flex-shrink: 0">
														<path d="M248,124a56.11,56.11,0,0,0-32-50.61V72a48,48,0,0,0-88-26.49A48,48,0,0,0,40,72v1.39a56,56,0,0,0,0,101.2V176a48,48,0,0,0,88,26.49A48,48,0,0,0,216,176v-1.41A56.09,56.09,0,0,0,248,124ZM88,208a32,32,0,0,1-31.81-28.56A55.87,55.87,0,0,0,64,180h8a8,8,0,0,0,0-16H64A40,40,0,0,1,50.67,86.27,8,8,0,0,0,56,78.73V72a32,32,0,0,1,64,0v68.26A47.8,47.8,0,0,0,88,128a8,8,0,0,0,0,16,32,32,0,0,1,0,64Zm104-44h-8a8,8,0,0,0,0,16h8a55.87,55.87,0,0,0,7.81-.56A32,32,0,1,1,168,144a8,8,0,0,0,0-16,47.8,47.8,0,0,0-32,12.26V72a32,32,0,0,1,64,0v6.73a8,8,0,0,0,5.33,7.54A40,40,0,0,1,192,164Zm16-52a8,8,0,0,1-8,8h-4a36,36,0,0,1-36-36V80a8,8,0,0,1,16,0v4a20,20,0,0,0,20,20h4A8,8,0,0,1,208,112ZM60,120H56a8,8,0,0,1,0-16h4A20,20,0,0,0,80,84V80a8,8,0,0,1,16,0v4A36,36,0,0,1,60,120Z"/>
													</svg>
													<span class="add-context-plus">+</span>
													<span class="add-context-label">Add to context</span>
												</span>
											</button>
										{/if}
									</div>
								{/if}
							</div>
						</li>
					{/each}
				</ul>
			{/each}
		{/if}
	</div>
{/if}

<DiagramDialog
	open={showCreateDiagramDialog}
	mode="create"
	onsave={handleCreateDiagram}
	oncancel={() => (showCreateDiagramDialog = false)}
/>

{#if showCreatePackageDialog}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div style="position: fixed; inset: 0; z-index: 50; display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.4)" onclick={() => (showCreatePackageDialog = false)}>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div class="rounded-lg p-6 shadow-lg" style="background: var(--color-surface); min-width: 360px" onclick={(e) => e.stopPropagation()}>
			<h3 class="mb-4 text-lg font-semibold" style="color: var(--color-fg)">Create Package</h3>
			<label class="mb-3 block text-sm" style="color: var(--color-fg)">
				Name
				<input
					bind:value={newPackageName}
					class="mt-1 block w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					placeholder="Package name"
				/>
			</label>
			<label class="mb-4 block text-sm" style="color: var(--color-fg)">
				Description
				<textarea
					bind:value={newPackageDescription}
					class="mt-1 block w-full rounded border px-3 py-2 text-sm"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
					rows="3"
					placeholder="Optional description"
				></textarea>
			</label>
			<div class="flex justify-end gap-2">
				<button onclick={() => (showCreatePackageDialog = false)} class="rounded border px-3 py-1.5 text-sm" style="border-color: var(--color-border); color: var(--color-fg)">Cancel</button>
				<button onclick={handleCreatePackage} disabled={!newPackageName.trim()} class="rounded px-3 py-1.5 text-sm text-white" style="background-color: var(--color-primary)">Create</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.add-context-btn {
		overflow: hidden;
		white-space: nowrap;
		width: 40px;
		padding-left: 8px;
		padding-right: 8px;
		transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	}
	.add-context-btn:hover {
		width: 128px;
	}
	.add-context-inner {
		display: flex;
		align-items: center;
		gap: 4px;
	}
	.add-context-btn .add-context-plus {
		display: inline-block;
		width: 8px;
		opacity: 1;
		transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.15s ease;
	}
	.add-context-btn:hover .add-context-plus {
		width: 0;
		opacity: 0;
	}
	.add-context-btn .add-context-label {
		display: inline-block;
		width: 0;
		overflow: hidden;
		opacity: 0;
		transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease 0.1s;
	}
	.add-context-btn:hover .add-context-label {
		width: 80px;
		opacity: 1;
	}
</style>
