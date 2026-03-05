<script lang="ts">
	/** Recursive tree node component for diagram hierarchy navigation. */
	import type { DiagramHierarchyNode } from '$lib/types/api';

	interface Props {
		node: DiagramHierarchyNode;
		depth?: number;
		currentDiagramId?: string;
		searchQuery?: string;
		showDiagramsOnly?: boolean;
		expandedIds?: Set<string>;
	}

	let {
		node,
		depth = 0,
		currentDiagramId = '',
		searchQuery = '',
		showDiagramsOnly = false,
		expandedIds = new Set<string>(),
	}: Props = $props();

	let expanded = $state(expandedIds.has(node.id) || depth < 2);

	const hasChildren = $derived(node.children && node.children.length > 0);
	const isCurrent = $derived(currentDiagramId === node.id);
	const matchesSearch = $derived(
		!searchQuery || node.name.toLowerCase().includes(searchQuery.toLowerCase())
	);
	const childMatchesSearch: boolean = $derived(
		!searchQuery ||
			(node.children ?? []).some(
				(c) =>
					c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
					(c.children ?? []).length > 0
			)
	);

	/** Recursively check if this node or any descendant has canvas content. */
	function descendantHasContent(n: DiagramHierarchyNode): boolean {
		return (n.children ?? []).some(
			(c) => c.has_content || descendantHasContent(c)
		);
	}

	/**
	 * Indicator type:
	 * - 'solid': node has canvas content (elements/participants on its canvas)
	 * - 'hollow': node has no content itself but a descendant does (organizational container)
	 * - 'none': no content anywhere in this subtree
	 */
	const isPackage = $derived(node.node_type === 'package');
	const indicatorType = $derived<'solid' | 'hollow' | 'none'>(
		node.has_content
			? 'solid'
			: descendantHasContent(node)
				? 'hollow'
				: 'none'
	);
	const nodeHref = $derived(isPackage ? `/packages/${node.id}` : `/diagrams/${node.id}`);

	const passesDiagramFilter = $derived(
		!showDiagramsOnly || node.has_content || descendantHasContent(node)
	);
	const visible = $derived((matchesSearch || childMatchesSearch) && passesDiagramFilter);

	function toggleExpand() {
		expanded = !expanded;
		if (expanded) {
			expandedIds.add(node.id);
		} else {
			expandedIds.delete(node.id);
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'ArrowRight' && hasChildren && !expanded) {
			event.preventDefault();
			expanded = true;
			expandedIds.add(node.id);
		} else if (event.key === 'ArrowLeft' && expanded) {
			event.preventDefault();
			expanded = false;
			expandedIds.delete(node.id);
		}
	}
</script>

{#if visible}
	<li
		role="treeitem"
		aria-expanded={hasChildren ? expanded : undefined}
		aria-current={isCurrent ? 'page' : undefined}
		class="tree-node"
	>
		<div
			class="tree-node__row"
			class:tree-node__row--current={isCurrent}
			style="padding-left: {depth * 20 + 8}px"
		>
			{#if hasChildren}
				<button
					onclick={toggleExpand}
					onkeydown={handleKeydown}
					class="tree-node__toggle"
					aria-label={expanded ? 'Collapse' : 'Expand'}
				>
					<span aria-hidden="true">{expanded ? '▼' : '▶'}</span>
				</button>
			{:else}
				<span class="tree-node__spacer" aria-hidden="true"></span>
			{/if}
			<a
				href={nodeHref}
				class="tree-node__link"
				onclick={() => { if (hasChildren && !expanded) { expanded = true; expandedIds.add(node.id); } }}
				onkeydown={handleKeydown}
			>
				{#if indicatorType === 'solid'}
					<span class="tree-node__diagram-indicator tree-node__diagram-indicator--solid" aria-hidden="true"></span>
				{:else if indicatorType === 'hollow'}
					<span class="tree-node__diagram-indicator tree-node__diagram-indicator--hollow" aria-hidden="true"></span>
				{/if}
				<span class="tree-node__name">{node.name}</span>
				{#if node.diagram_type}
					<span class="tree-node__type">{node.diagram_type}</span>
				{:else if isPackage}
					<span class="tree-node__type tree-node__type--package">pkg</span>
				{/if}
			</a>
		</div>
		{#if hasChildren && expanded}
			<ul role="group" class="tree-node__children">
				{#each node.children as child (child.id)}
					<svelte:self
						node={child}
						depth={depth + 1}
						{currentDiagramId}
						{searchQuery}
						{showDiagramsOnly}
						{expandedIds}
					/>
				{/each}
			</ul>
		{/if}
	</li>
{/if}

<style>
	.tree-node__row {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 2px 8px;
		border-radius: 4px;
	}
	.tree-node__row:hover {
		background-color: var(--color-bg);
	}
	.tree-node__row--current {
		background-color: var(--color-bg);
		font-weight: 600;
	}
	.tree-node__toggle {
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
	.tree-node__spacer {
		width: 18px;
		flex-shrink: 0;
	}
	.tree-node__link {
		display: flex;
		align-items: center;
		gap: 8px;
		text-decoration: none;
		color: var(--color-fg);
		font-size: 0.875rem;
		flex: 1;
		min-width: 0;
		padding: 2px 0;
	}
	.tree-node__diagram-indicator {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 2px;
		flex-shrink: 0;
	}
	.tree-node__diagram-indicator--solid {
		background-color: var(--color-primary);
	}
	.tree-node__diagram-indicator--hollow {
		background-color: transparent;
		border: 1.5px solid var(--color-primary);
	}
	.tree-node__name {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.tree-node__type {
		font-size: 0.7rem;
		color: var(--color-muted);
		flex-shrink: 0;
		background: var(--color-surface);
		padding: 1px 6px;
		border-radius: 4px;
	}
	.tree-node__type--package {
		opacity: 0.6;
		font-style: italic;
	}
	.tree-node__children {
		list-style: none;
		padding: 0;
		margin: 0;
	}
</style>
