<script lang="ts">
	import { page } from '$app/state';
	import { GUIDE_SECTIONS } from '$lib/guide';

	let { children } = $props();

	// Active section = /guide/<slug>; /guide root renders the first
	// section directly (+page.svelte redirects to it).
	const activeSlug = $derived(page.params.section ?? GUIDE_SECTIONS[0].slug);
</script>

<div class="guide-wrapper">
	<nav aria-label="User guide sections" class="guide-nav">
		<h2 class="mb-3 text-xs font-semibold uppercase" style="color: var(--color-muted)">
			User Guide
		</h2>
		<ul class="space-y-1">
			{#each GUIDE_SECTIONS as section}
				<li>
					<a
						href="/guide/{section.slug}"
						class="guide-link block rounded px-2 py-1 text-sm"
						class:active={activeSlug === section.slug}
						aria-current={activeSlug === section.slug ? 'page' : undefined}
					>
						{section.title}
					</a>
				</li>
			{/each}
		</ul>
	</nav>

	<article class="guide-content">
		{@render children()}
	</article>
</div>

<style>
	.guide-wrapper {
		display: grid;
		grid-template-columns: 220px 1fr;
		gap: 2rem;
		align-items: start;
	}
	.guide-nav {
		position: sticky;
		top: 1rem;
		padding: 1rem;
		border-radius: 8px;
		border: 1px solid var(--color-border);
		background: var(--color-surface);
	}
	.guide-link {
		color: var(--color-fg);
		text-decoration: none;
	}
	.guide-link:hover {
		background: var(--color-bg);
	}
	.guide-link.active {
		background: var(--color-bg);
		font-weight: 600;
	}
	/* Typography for rendered markdown lives in MarkdownView.svelte (single
	   source of truth — protocol #13). The guide layout only owns the page
	   chrome (sticky nav, grid, narrow-screen breakpoint). */
	@media (max-width: 768px) {
		.guide-wrapper {
			grid-template-columns: 1fr;
		}
		.guide-nav {
			position: static;
		}
	}
</style>
