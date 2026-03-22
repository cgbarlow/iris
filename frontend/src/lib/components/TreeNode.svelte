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
		siblings?: DiagramHierarchyNode[];
		onreorder?: (parentId: string | null, orderedIds: string[]) => void;
	}

	let {
		node,
		depth = 0,
		currentDiagramId = '',
		searchQuery = '',
		showDiagramsOnly = false,
		expandedIds = new Set<string>(),
		siblings = [],
		onreorder,
	}: Props = $props();

	let expanded = $state(expandedIds.has(node.id) || depth < 2);
	let dropPosition = $state<'before' | 'after' | null>(null);

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

	// Drag-and-drop reordering
	function handleDragStart(e: DragEvent) {
		if (!e.dataTransfer || !onreorder) return;
		e.dataTransfer.effectAllowed = 'move';
		e.dataTransfer.setData('text/plain', JSON.stringify({
			id: node.id,
			parentId: node.parent_package_id,
		}));
	}

	function handleDragOver(e: DragEvent) {
		if (!e.dataTransfer || !onreorder) return;
		e.preventDefault();
		e.dataTransfer.dropEffect = 'move';

		const target = e.currentTarget as HTMLElement;
		const rect = target.getBoundingClientRect();
		const midY = rect.top + rect.height / 2;
		dropPosition = e.clientY < midY ? 'before' : 'after';
	}

	function handleDragLeave() {
		dropPosition = null;
	}

	function handleDrop(e: DragEvent) {
		if (!e.dataTransfer || !onreorder) return;
		e.preventDefault();

		let dragData: { id: string; parentId: string | null };
		try {
			dragData = JSON.parse(e.dataTransfer.getData('text/plain'));
		} catch {
			dropPosition = null;
			return;
		}

		// Can't drop on itself
		if (dragData.id === node.id) {
			dropPosition = null;
			return;
		}

		// Compute new order — insert dragged item among target's siblings
		const currentOrder = siblings.map((s) => s.id);
		const filtered = currentOrder.filter((id) => id !== dragData.id);
		const targetIndex = filtered.indexOf(node.id);
		const insertIndex = dropPosition === 'before' ? targetIndex : targetIndex + 1;
		filtered.splice(insertIndex, 0, dragData.id);

		onreorder(node.parent_package_id, filtered);
		dropPosition = null;
	}
</script>

{#if visible}
	<li
		role="treeitem"
		aria-expanded={hasChildren ? expanded : undefined}
		aria-current={isCurrent ? 'page' : undefined}
		class="tree-node"
	>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="tree-node__row"
			class:tree-node__row--current={isCurrent}
			class:tree-node__row--drop-before={dropPosition === 'before'}
			class:tree-node__row--drop-after={dropPosition === 'after'}
			style="padding-left: {depth * 20 + 8}px"
			draggable={onreorder ? 'true' : undefined}
			ondragstart={handleDragStart}
			ondragover={handleDragOver}
			ondragleave={handleDragLeave}
			ondrop={handleDrop}
		>
			{#if onreorder}
				<span class="tree-node__grip" aria-hidden="true">⠿</span>
			{/if}
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
				title={node.diagram_type ? node.diagram_type : isPackage ? 'package' : undefined}
				onclick={() => { if (hasChildren && !expanded) { expanded = true; expandedIds.add(node.id); } }}
				onkeydown={handleKeydown}
			>
				{#if indicatorType === 'solid'}
					<span class="tree-node__diagram-indicator tree-node__diagram-indicator--solid" aria-hidden="true"></span>
				{:else if indicatorType === 'hollow'}
					<span class="tree-node__diagram-indicator tree-node__diagram-indicator--hollow" aria-hidden="true"></span>
				{/if}
				<span class="tree-node__name">{node.name}</span>
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
						siblings={node.children}
						{onreorder}
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
		position: relative;
	}
	.tree-node__row:hover {
		background-color: var(--color-bg);
	}
	.tree-node__row--current {
		background-color: var(--color-bg);
		font-weight: 600;
	}
	.tree-node__row--drop-before {
		border-top: 2px solid var(--color-primary);
	}
	.tree-node__row--drop-after {
		border-bottom: 2px solid var(--color-primary);
	}
	.tree-node__row[draggable='true'] {
		cursor: grab;
	}
	.tree-node__row[draggable='true']:active {
		cursor: grabbing;
	}
	.tree-node__grip {
		display: none;
		width: 14px;
		font-size: 10px;
		color: var(--color-muted);
		flex-shrink: 0;
		cursor: grab;
		user-select: none;
	}
	.tree-node__row:hover .tree-node__grip {
		display: flex;
		align-items: center;
		justify-content: center;
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
