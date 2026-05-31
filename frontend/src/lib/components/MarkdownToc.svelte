<script lang="ts">
	/**
	 * MarkdownToc: right-side TOC drawer for Text diagrams (ADR-137).
	 *
	 * Mirrors the CommentsPanel right-drawer pattern used by the diagram
	 * detail page (300px, surface fill, 6px border-radius). Indentation
	 * scales with heading depth; clicking a heading scrolls to the rendered
	 * heading element by id (slugged from heading text).
	 */
	import type { TocHeading } from './MarkdownView.svelte';
	import { viewport } from '$lib/stores/viewport.svelte';

	interface Props {
		headings: TocHeading[];
		/** Optional close callback to match CommentsPanel's onclose contract. */
		onclose?: () => void;
	}

	let { headings, onclose }: Props = $props();

	function jump(id: string) {
		const el = document.getElementById(id);
		el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
		// On mobile the TOC is a full-screen overlay drawer (ADR-229); close it
		// after jumping so the reader lands on the content.
		if (viewport.isMobile) onclose?.();
	}
</script>

<!-- Mobile (ADR-229): the TOC becomes a fixed right overlay drawer; this
     backdrop closes it on tap. On desktop it's an inline column (no backdrop). -->
{#if viewport.isMobile && onclose}
	<button type="button" class="md-toc-backdrop" aria-label="Close TOC" onclick={onclose}></button>
{/if}
<aside class="md-toc" aria-label="Table of contents">
	<header class="md-toc__header">
		<span class="md-toc__title">Contents</span>
		{#if onclose}
			<button type="button" class="md-toc__close" onclick={onclose} aria-label="Close TOC">✕</button>
		{/if}
	</header>
	{#if headings.length === 0}
		<div class="md-toc__empty">No headings.</div>
	{:else}
		<ul class="md-toc__list" role="list">
			{#each headings as h (h.id)}
				<li
					class="md-toc__item md-toc__item--lvl-{h.level}"
					style="--md-toc-indent: {(h.level - 1) * 12}px;"
				>
					<button type="button" onclick={() => jump(h.id)}>
						<span class="md-toc__text">{h.text}</span>
					</button>
				</li>
			{/each}
		</ul>
	{/if}
</aside>

<style>
	.md-toc {
		display: flex; flex-direction: column;
		width: 300px;
		max-height: 100%;
		background: var(--color-surface, #ffffff);
		border: 1px solid var(--color-border, #e5e7eb);
		border-radius: 6px;
		padding: 12px;
		font-size: 12px;
		overflow-y: auto;
	}

	/* Mobile (ADR-229): a fixed right overlay drawer instead of a 300px column
	   that would squeeze the markdown content to nothing on a phone. */
	.md-toc-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		z-index: 49;
		border: 0;
	}
	@media (max-width: 767px) {
		.md-toc {
			position: fixed;
			right: 0; top: 0; bottom: 0;
			height: 100dvh;
			width: 85vw; max-width: 320px;
			border-radius: 0;
			z-index: 50;
		}
	}
	.md-toc__header {
		display: flex; justify-content: space-between; align-items: center;
		margin-bottom: 8px;
	}
	.md-toc__title { font-weight: 600; }
	.md-toc__close { background: transparent; border: 0; cursor: pointer; font-size: 14px; }
	.md-toc__empty { color: var(--color-muted, #6b7280); padding: 8px 0; text-align: center; }
	.md-toc__list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 1px; }
	.md-toc__item button {
		display: block;
		width: 100%;
		padding: 4px 6px 4px calc(6px + var(--md-toc-indent, 0px));
		background: transparent; border: 0;
		text-align: left; cursor: pointer;
		color: var(--color-fg, #202931);
		font-size: 12px;
		border-radius: 4px;
	}
	.md-toc__item--lvl-1 button { font-weight: 600; }
	.md-toc__item button:hover { background: var(--color-surface-hover, #f3f4f6); }
	.md-toc__text { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
