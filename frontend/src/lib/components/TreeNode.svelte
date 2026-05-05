<script lang="ts">
	/** Recursive tree node component for diagram hierarchy navigation. */
	import type { DiagramHierarchyNode } from '$lib/types/api';

	interface Props {
		node: DiagramHierarchyNode;
		depth?: number;
		currentDiagramId?: string;
		searchQuery?: string;
		showDiagramsOnly?: boolean;
		/** Issue #27: per-kind visibility toggles from the Show dropdown. */
		showDiagrams?: boolean;
		showText?: boolean;
		expandedIds?: Set<string>;
		siblings?: DiagramHierarchyNode[];
		onreorder?: (parentId: string | null, orderedIds: string[]) => void;
		contextItemIds?: Set<string>;
		onaddcontext?: (node: DiagramHierarchyNode) => void;
		onremovecontext?: (id: string) => void;
		onhover?: (nodeId: string | null, nodeName: string | null) => void;
		graphHoverIds?: Set<string>;
		peekExpandedIds?: Set<string>;
		autoExpandDepth?: number;
	}

	let {
		node,
		depth = 0,
		currentDiagramId = '',
		searchQuery = '',
		showDiagramsOnly = false,
		showDiagrams = true,
		showText = true,
		expandedIds = new Set<string>(),
		siblings = [],
		onreorder,
		contextItemIds,
		onaddcontext,
		onremovecontext,
		onhover,
		graphHoverIds,
		peekExpandedIds,
		autoExpandDepth = 2,
	}: Props = $props();

	const isGraphHighlighted = $derived(graphHoverIds?.has(node.id) ?? false);
	const isPeeked = $derived(peekExpandedIds?.has(node.id) ?? false);

	let expanded = $state(expandedIds.has(node.id) || depth < autoExpandDepth);
	let effectiveExpanded = $derived(expanded || isPeeked);
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
	const nodeHref = $derived(isPackage ? `/packages/${node.id}` : `/views/${node.id}`);

	const passesDiagramFilter = $derived(
		!showDiagramsOnly || node.has_content || descendantHasContent(node)
	);
	/** Issue #27: hide leaf nodes whose kind is toggled off; packages are always shown. */
	const isText = $derived(node.diagram_type === 'text');
	const passesKindFilter = $derived(
		isPackage || (isText ? showText : showDiagrams),
	);
	const visible = $derived(
		(matchesSearch || childMatchesSearch) && passesDiagramFilter && passesKindFilter,
	);

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
		aria-expanded={hasChildren ? effectiveExpanded : undefined}
		aria-current={isCurrent ? 'page' : undefined}
		class="tree-node"
	>
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="tree-node__row"
			class:tree-node__row--current={isCurrent}
			class:tree-node__row--graph-highlight={isGraphHighlighted}
			class:tree-node__row--drop-before={dropPosition === 'before'}
			class:tree-node__row--drop-after={dropPosition === 'after'}
			style="padding-left: {depth * 20 + 8}px"
			draggable={onreorder ? 'true' : undefined}
			ondragstart={handleDragStart}
			ondragover={handleDragOver}
			ondragleave={handleDragLeave}
			ondrop={handleDrop}
			onmouseenter={() => onhover?.(node.id, node.name)}
			onmouseleave={() => onhover?.(null, null)}
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
					<span aria-hidden="true">{effectiveExpanded ? '▼' : '▶'}</span>
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
				<!-- Issue #26: text-class diagrams render their label in the muted colour
					 to visually distinguish them from "true" diagrams. -->
				<span
					class="tree-node__name"
					class:tree-node__name--text={node.diagram_type === 'text'}
				>{node.name}</span>
			</a>
			{#if onaddcontext && onremovecontext && contextItemIds}
				{#if contextItemIds.has(node.id)}
					<button
						onclick={(e) => { e.preventDefault(); e.stopPropagation(); onremovecontext(node.id); }}
						class="tree-node__ctx-added rounded border px-2 py-1 text-xs"
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
						onclick={(e) => { e.preventDefault(); e.stopPropagation(); onaddcontext(node); }}
						class="tree-node__ctx-add rounded border py-1 text-xs"
						style="border-color: var(--color-border); background: var(--color-surface); color: var(--color-primary); cursor: pointer"
						title="Add to Iris AI context"
					>
						<span class="tree-node__ctx-add-inner">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="12" height="12" aria-hidden="true" style="flex-shrink: 0">
								<path d="M248,124a56.11,56.11,0,0,0-32-50.61V72a48,48,0,0,0-88-26.49A48,48,0,0,0,40,72v1.39a56,56,0,0,0,0,101.2V176a48,48,0,0,0,88,26.49A48,48,0,0,0,216,176v-1.41A56.09,56.09,0,0,0,248,124ZM88,208a32,32,0,0,1-31.81-28.56A55.87,55.87,0,0,0,64,180h8a8,8,0,0,0,0-16H64A40,40,0,0,1,50.67,86.27,8,8,0,0,0,56,78.73V72a32,32,0,0,1,64,0v68.26A47.8,47.8,0,0,0,88,128a8,8,0,0,0,0,16,32,32,0,0,1,0,64Zm104-44h-8a8,8,0,0,0,0,16h8a55.87,55.87,0,0,0,7.81-.56A32,32,0,1,1,168,144a8,8,0,0,0,0-16,47.8,47.8,0,0,0-32,12.26V72a32,32,0,0,1,64,0v6.73a8,8,0,0,0,5.33,7.54A40,40,0,0,1,192,164Zm16-52a8,8,0,0,1-8,8h-4a36,36,0,0,1-36-36V80a8,8,0,0,1,16,0v4a20,20,0,0,0,20,20h4A8,8,0,0,1,208,112ZM60,120H56a8,8,0,0,1,0-16h4A20,20,0,0,0,80,84V80a8,8,0,0,1,16,0v4A36,36,0,0,1,60,120Z"/>
							</svg>
							<span class="tree-node__ctx-plus">+</span>
							<span class="tree-node__ctx-label">Add to context</span>
						</span>
					</button>
				{/if}
			{/if}
		</div>
		{#if hasChildren && effectiveExpanded}
			<ul role="group" class="tree-node__children">
				{#each node.children as child (child.id)}
					<svelte:self
						node={child}
						depth={depth + 1}
						{currentDiagramId}
						{searchQuery}
						{showDiagramsOnly}
						{showDiagrams}
						{showText}
						{expandedIds}
						siblings={node.children}
						{onreorder}
						{contextItemIds}
						{onaddcontext}
						{onremovecontext}
						{onhover}
						{graphHoverIds}
						{peekExpandedIds}
						{autoExpandDepth}
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
	.tree-node__row--graph-highlight {
		background-color: var(--color-bg);
		outline: 2px solid var(--color-primary);
		outline-offset: -2px;
		border-radius: 4px;
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
	.tree-node__name--text {
		color: var(--color-muted);
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
	/* Add-to-context button (matches search pattern) */
	.tree-node__ctx-add {
		display: none;
		overflow: hidden;
		white-space: nowrap;
		width: 40px;
		padding-left: 8px;
		padding-right: 8px;
		flex-shrink: 0;
		transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	}
	.tree-node__row:hover .tree-node__ctx-add {
		display: inline-block;
	}
	.tree-node__ctx-add:hover {
		width: 128px;
	}
	.tree-node__ctx-add-inner {
		display: flex;
		align-items: center;
		gap: 4px;
	}
	.tree-node__ctx-add .tree-node__ctx-plus {
		display: inline-block;
		width: 8px;
		opacity: 1;
		transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.15s ease;
	}
	.tree-node__ctx-add:hover .tree-node__ctx-plus {
		width: 0;
		opacity: 0;
	}
	.tree-node__ctx-add .tree-node__ctx-label {
		display: inline-block;
		width: 0;
		overflow: hidden;
		opacity: 0;
		transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease 0.1s;
	}
	.tree-node__ctx-add:hover .tree-node__ctx-label {
		width: 80px;
		opacity: 1;
	}
</style>
