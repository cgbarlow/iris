<script lang="ts">
	/**
	 * Shared hierarchy sidebar (ADR-232) — the navigable package / diagram /
	 * element tree used across dashboard, views, package and element screens.
	 * Owns search, the Show toggles, the Reorder mode, and collapsed-by-default
	 * expansion (auto-revealing the current node's ancestors). The host page
	 * controls visibility via `bind:open` and renders its own toggle button.
	 */
	import { apiFetch } from '$lib/utils/api';
	import type { DiagramHierarchyNode } from '$lib/types/api';
	import HierarchyControls from '$lib/components/HierarchyControls.svelte';
	import TreeNode from '$lib/components/TreeNode.svelte';
	import { viewport } from '$lib/stores/viewport.svelte';

	interface Props {
		setId?: string | null;
		/** Highlight + reveal this node (a diagram, package or element id). */
		currentId?: string;
		open?: boolean;
		oncreateview?: () => void;
		oncreatepackage?: () => void;
		oncreateelement?: () => void;
	}

	let {
		setId,
		currentId = '',
		open = $bindable(true),
		oncreateview,
		oncreatepackage,
		oncreateelement,
	}: Props = $props();

	let tree = $state<DiagramHierarchyNode[]>([]);
	let loading = $state(false);
	let search = $state('');
	let showDiagrams = $state(true);
	let showText = $state(true);
	let reorderMode = $state(false);
	let expandedIds = $state<Set<string>>(new Set());
	let loadedFor = '';

	/** Collect the ancestor chain of `targetId` so the current node is visible
	 * even though the tree defaults to collapsed (ADR-232 issue 5). */
	function ancestorsOf(nodes: DiagramHierarchyNode[], targetId: string): Set<string> {
		const found = new Set<string>();
		const walk = (n: DiagramHierarchyNode, chain: string[]): boolean => {
			if (n.id === targetId) { chain.forEach((id) => found.add(id)); return true; }
			for (const c of n.children ?? []) if (walk(c, [...chain, n.id])) return true;
			return false;
		};
		for (const r of nodes) walk(r, []);
		return found;
	}

	async function load() {
		if (!setId) { tree = []; return; }
		loading = true;
		try {
			tree = await apiFetch<DiagramHierarchyNode[]>(
				`/api/diagrams/hierarchy?set_id=${encodeURIComponent(setId)}`,
			);
			expandedIds = currentId ? ancestorsOf(tree, currentId) : new Set();
		} catch {
			tree = [];
		}
		loading = false;
	}

	$effect(() => {
		if (open && setId && loadedFor !== setId) { loadedFor = setId; void load(); }
	});

	async function handleReorder(parentId: string | null, orderedIds: string[]) {
		try {
			await apiFetch('/api/diagrams/reorder', {
				method: 'PUT',
				body: JSON.stringify({ parent_package_id: parentId, ordered_ids: orderedIds }),
			});
		} finally {
			await load();
		}
	}
</script>

{#if open && viewport.isMobile}
	<button type="button" class="drawer-backdrop" aria-label="Close hierarchy" onclick={() => (open = false)}></button>
{/if}
{#if open}
	<aside
		data-hierarchy-sidebar
		style="width: 280px; max-height: calc(100vh - 80px); flex-shrink: 0"
		class="overflow-y-auto rounded border"
		style:border-color="var(--color-border)"
		style:background-color="var(--color-surface)"
		aria-label="Hierarchy"
	>
		<div class="flex items-center justify-between p-3" style="border-bottom: 1px solid var(--color-border)">
			<span class="text-sm font-semibold" style="color: var(--color-fg)">Hierarchy</span>
			<div class="flex items-center gap-2">
				<HierarchyControls
					{showDiagrams}
					{showText}
					onShowDiagrams={(v) => (showDiagrams = v)}
					onShowText={(v) => (showText = v)}
					{oncreateview}
					{oncreatepackage}
					{oncreateelement}
				/>
				<button
					onclick={() => (reorderMode = !reorderMode)}
					class="rounded px-2 py-1 text-xs"
					style="border: 1px solid {reorderMode ? 'var(--color-primary)' : 'var(--color-border)'}; background: {reorderMode ? 'var(--color-primary)' : 'transparent'}; color: {reorderMode ? 'white' : 'var(--color-muted)'}"
					title={reorderMode ? 'Done — exit reorder mode' : 'Reorder — drag tree items to change their position'}
				>
					{reorderMode ? 'Done' : 'Reorder'}
				</button>
				<button onclick={() => (open = false)} class="rounded p-1 text-xs" style="color: var(--color-muted)" aria-label="Close sidebar">✕</button>
			</div>
		</div>
		<div class="p-2">
			<input
				type="search"
				placeholder="Search tree..."
				bind:value={search}
				class="w-full rounded border px-2 py-1 text-xs"
				style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				aria-label="Search hierarchy"
			/>
		</div>
		<div class="px-2 pb-2">
			{#if loading}
				<p class="p-2 text-xs" style="color: var(--color-muted)">Loading...</p>
			{:else if tree.length === 0}
				<p class="p-2 text-xs" style="color: var(--color-muted)">Nothing here yet.</p>
			{:else}
				<ul role="tree">
					{#each tree as node (node.id)}
						<TreeNode
							{node}
							currentDiagramId={currentId}
							searchQuery={search}
							{showDiagrams}
							{showText}
							{expandedIds}
							siblings={tree}
							onreorder={reorderMode ? handleReorder : undefined}
						/>
					{/each}
				</ul>
			{/if}
		</div>
	</aside>
{/if}
