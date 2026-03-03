<script lang="ts">
	/** Recursive tree node component for model hierarchy navigation. */
	import type { ModelHierarchyNode } from '$lib/types/api';

	interface Props {
		node: ModelHierarchyNode;
		depth?: number;
		currentModelId?: string;
		searchQuery?: string;
		showModelsOnly?: boolean;
		expandedIds?: Set<string>;
	}

	let {
		node,
		depth = 0,
		currentModelId = '',
		searchQuery = '',
		showModelsOnly = false,
		expandedIds = new Set<string>(),
	}: Props = $props();

	let expanded = $state(expandedIds.has(node.id) || depth < 2);

	const hasChildren = $derived(node.children && node.children.length > 0);
	const isCurrent = $derived(currentModelId === node.id);
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
	function descendantHasContent(n: ModelHierarchyNode): boolean {
		return (n.children ?? []).some(
			(c) => c.has_content || descendantHasContent(c)
		);
	}

	/**
	 * Indicator type:
	 * - 'solid': node has canvas content (entities/participants on its canvas)
	 * - 'hollow': node has no content itself but a descendant does (organizational container)
	 * - 'none': no content anywhere in this subtree
	 */
	const indicatorType = $derived<'solid' | 'hollow' | 'none'>(
		node.has_content
			? 'solid'
			: descendantHasContent(node)
				? 'hollow'
				: 'none'
	);

	const passesModelFilter = $derived(
		!showModelsOnly || node.has_content || descendantHasContent(node)
	);
	const visible = $derived((matchesSearch || childMatchesSearch) && passesModelFilter);

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
				href="/models/{node.id}"
				class="tree-node__link"
				onkeydown={handleKeydown}
			>
				{#if indicatorType === 'solid'}
					<span class="tree-node__model-indicator tree-node__model-indicator--solid" aria-hidden="true"></span>
				{:else if indicatorType === 'hollow'}
					<span class="tree-node__model-indicator tree-node__model-indicator--hollow" aria-hidden="true"></span>
				{/if}
				<span class="tree-node__name">{node.name}</span>
				<span class="tree-node__type">{node.model_type}</span>
			</a>
		</div>
		{#if hasChildren && expanded}
			<ul role="group" class="tree-node__children">
				{#each node.children as child (child.id)}
					<svelte:self
						node={child}
						depth={depth + 1}
						{currentModelId}
						{searchQuery}
						{showModelsOnly}
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
	.tree-node__model-indicator {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 2px;
		flex-shrink: 0;
	}
	.tree-node__model-indicator--solid {
		background-color: var(--color-primary);
	}
	.tree-node__model-indicator--hollow {
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
	.tree-node__children {
		list-style: none;
		padding: 0;
		margin: 0;
	}
</style>
