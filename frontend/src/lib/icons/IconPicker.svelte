<script lang="ts">
	/**
	 * IconPicker: Modal for browsing, searching, and selecting icons (ADR-091-C).
	 * Shows icons from the tag index grouped by category with semantic search.
	 * Uses the same matching algorithm as the backend SemanticIconMatcher
	 * (weighted tokens, head-noun emphasis, synonym expansion, stemming).
	 */
	import type { IconRef } from '$lib/types/canvas';
	import { ICON_TAGS, ICON_CATEGORIES, type IconTagEntry } from './iconTags';
	import { semanticSearch } from './semanticSearch';
	import IconDisplay from './IconDisplay.svelte';

	interface Props {
		open: boolean;
		onselect: (icon: IconRef) => void;
		onclose: () => void;
	}

	let { open, onselect, onclose }: Props = $props();

	let searchQuery = $state('');
	let selectedCategory = $state<string | null>(null);

	const filteredIcons = $derived.by(() => {
		let icons = ICON_TAGS;

		if (selectedCategory) {
			icons = icons.filter((e) => e.category === selectedCategory);
		}

		if (searchQuery.trim()) {
			const results = semanticSearch(searchQuery, icons);
			// Only show icons that actually scored > 0
			return results.filter((r) => r.score > 0).map((r) => r.entry);
		}

		return icons;
	});

	function handleSelect(entry: IconTagEntry) {
		onselect({ set: 'lucide', name: entry.name });
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onclose();
	}
</script>

{#if open}
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div class="icon-picker-overlay" role="dialog" aria-label="Icon picker" onkeydown={handleKeydown}>
		<div class="icon-picker">
			<div class="icon-picker__header">
				<h3 class="text-sm font-semibold">Select Icon</h3>
				<button onclick={onclose} class="icon-picker__close" aria-label="Close">✕</button>
			</div>

			<div class="icon-picker__search">
				<input
					type="text"
					placeholder="Search icons..."
					bind:value={searchQuery}
					class="w-full rounded border px-2 py-1 text-xs"
					style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
				/>
			</div>

			<div class="icon-picker__categories">
				<button
					class="icon-picker__cat-btn"
					class:icon-picker__cat-btn--active={!selectedCategory}
					onclick={() => (selectedCategory = null)}
				>
					All
				</button>
				{#each ICON_CATEGORIES as cat}
					<button
						class="icon-picker__cat-btn"
						class:icon-picker__cat-btn--active={selectedCategory === cat}
						onclick={() => (selectedCategory = cat)}
					>
						{cat}
					</button>
				{/each}
			</div>

			<div class="icon-picker__grid">
				{#each filteredIcons as entry}
					<button
						class="icon-picker__item"
						title={entry.name}
						onclick={() => handleSelect(entry)}
					>
						<IconDisplay icon={{ set: 'lucide', name: entry.name }} size={20} />
						<span class="icon-picker__item-name">{entry.name}</span>
					</button>
				{/each}
				{#if filteredIcons.length === 0}
					<p class="icon-picker__empty">No icons match your search.</p>
				{/if}
			</div>
		</div>
	</div>
{/if}

<style>
	.icon-picker-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.3);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
	}
	.icon-picker {
		background: var(--color-surface, #fff);
		border: 1px solid var(--color-border, #e5e7eb);
		border-radius: 8px;
		width: 420px;
		max-height: 500px;
		display: flex;
		flex-direction: column;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
	}
	.icon-picker__header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 12px 16px;
		border-bottom: 1px solid var(--color-border, #e5e7eb);
	}
	.icon-picker__close {
		background: none;
		border: none;
		font-size: 16px;
		cursor: pointer;
		color: var(--color-muted, #6b7280);
	}
	.icon-picker__search {
		padding: 8px 16px;
	}
	.icon-picker__categories {
		display: flex;
		flex-wrap: wrap;
		gap: 4px;
		padding: 4px 16px 8px;
	}
	.icon-picker__cat-btn {
		font-size: 10px;
		padding: 2px 8px;
		border-radius: 12px;
		border: 1px solid var(--color-border, #e5e7eb);
		background: transparent;
		color: var(--color-muted, #6b7280);
		cursor: pointer;
		text-transform: capitalize;
	}
	.icon-picker__cat-btn--active {
		background: var(--color-primary, #3b82f6);
		color: white;
		border-color: var(--color-primary, #3b82f6);
	}
	.icon-picker__grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(70px, 1fr));
		gap: 4px;
		padding: 8px 16px 16px;
		overflow-y: auto;
		flex: 1;
	}
	.icon-picker__item {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2px;
		padding: 6px 4px;
		border: 1px solid transparent;
		border-radius: 4px;
		cursor: pointer;
		background: transparent;
		color: var(--color-fg, #111);
		min-height: 52px;
	}
	.icon-picker__item :global(svg) {
		flex-shrink: 0;
	}
	.icon-picker__item:hover {
		background: var(--color-hover, #f3f4f6);
		border-color: var(--color-border, #e5e7eb);
	}
	.icon-picker__item-name {
		font-size: 9px;
		color: var(--color-muted, #6b7280);
		text-align: center;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		max-width: 100%;
	}
	.icon-picker__empty {
		grid-column: 1 / -1;
		text-align: center;
		color: var(--color-muted, #6b7280);
		font-size: 12px;
		padding: 16px;
	}
</style>
