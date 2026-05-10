<script lang="ts">
	/**
	 * MarkdownView: shared markdown renderer (ADR-137).
	 *
	 * Used by both the User Guide (`/guide/[section]/+page.svelte`) and the
	 * Text diagram canvas (`TextCanvas.svelte`) — DRY consolidation per
	 * issue #26.
	 *
	 * Pipeline:
	 *   markdown source → marked.parse → URL-scheme allowlist + iris://
	 *   rewrite → DOMPurify → {@html}
	 *
	 * Security: DOMPurify enforced per protocol #7. URL schemes restricted
	 * to {http, https, mailto, iris} so neither marked-output nor inline
	 * authoring can smuggle javascript:/data:/file: URIs.
	 *
	 * iris:// links: `iris://diagram/<id>` and `iris://element/<id>` are
	 * intercepted on click → SvelteKit `goto`. Diagram-link targets that
	 * are themselves Text documents (resolved via the optional
	 * `textDiagramIds` set) render with a muted colour to satisfy issue
	 * #26's grey-vs-black visual distinction.
	 */
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import {
		extractHeadings,
		renderMarkdown,
		type ExtractedLink,
		type TocHeading,
	} from './markdownHelpers';
	import { runMermaidIn, type MermaidTheme } from './markdownMermaidRender';
	export type { ExtractedLink, TocHeading } from './markdownHelpers';

	interface Props {
		source: string;
		/** Set of diagram IDs that are Text-class. Their refs render muted. */
		textDiagramIds?: Set<string>;
		/** Called once per render with the heading list (used by MarkdownToc). */
		onheadings?: (headings: TocHeading[]) => void;
		/** Called once per render with the iris:// links found in the source. */
		onlinks?: (links: ExtractedLink[]) => void;
	}

	let { source, textDiagramIds, onheadings, onlinks }: Props = $props();

	const rendered = $derived(renderMarkdown(source, textDiagramIds));
	const html = $derived(rendered.html);
	const headings = $derived(extractHeadings(source));

	$effect(() => { onheadings?.(headings); });
	$effect(() => { onlinks?.(rendered.links); });

	function onClick(e: MouseEvent) {
		const t = (e.target as HTMLElement | null)?.closest('a.md-iris-link');
		if (!t) return;
		const kind = t.getAttribute('data-iris-kind');
		const id = t.getAttribute('data-iris-id');
		if (!kind || !id) return;
		e.preventDefault();
		const path = kind === 'diagram' ? `/views/${id}` : `/elements/${id}`;
		goto(path);
	}

	// ADR-149: mermaid runs after {@html} injects placeholders.
	let rootEl: HTMLDivElement | undefined = $state();
	let theme: MermaidTheme = $state('default');

	function readTheme(): MermaidTheme {
		return document.documentElement.classList.contains('dark') ? 'dark' : 'default';
	}

	$effect(() => {
		// Re-run when html changes (new content) or theme flips.
		void html;
		void theme;
		if (!rootEl) return;
		void runMermaidIn(rootEl, theme);
	});

	onMount(() => {
		// Headings/links are emitted via queueMicrotask after the first $derived run.
		void headings;
		void html;
		theme = readTheme();
		const observer = new MutationObserver(() => {
			const next = readTheme();
			if (next !== theme) theme = next;
		});
		observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
		return () => observer.disconnect();
	});
</script>

<div bind:this={rootEl} class="md-view" onclick={onClick} role="presentation">
	<!-- Sanitised markdown — pipeline above enforces protocol #7. -->
	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	{@html html}
</div>

<style>
	/* Issue #32 reopen: typographic rules consolidated here as the
	   single source of truth for rendered markdown (protocol #13).
	   Both the User Guide and Text views now share these. */
	.md-view :global(h1) {
		font-size: 1.875rem; font-weight: bold;
		margin: 0.5em 0 0.5em; line-height: 1.25;
		color: var(--color-fg);
	}
	.md-view :global(h2) {
		font-size: 1.25rem; font-weight: 600;
		margin: 1.6em 0 0.5em; line-height: 1.3;
		color: var(--color-fg);
	}
	.md-view :global(h3) {
		font-size: 1.05rem; font-weight: 600;
		margin: 1.4em 0 0.5em; line-height: 1.35;
		color: var(--color-fg);
	}
	.md-view :global(h4), .md-view :global(h5), .md-view :global(h6) {
		font-weight: 600;
		margin: 1.2em 0 0.4em; line-height: 1.35;
		color: var(--color-fg);
	}
	.md-view :global(p) {
		color: var(--color-fg);
		line-height: 1.6;
		margin: 0 0 1rem;
	}
	.md-view :global(ul) {
		color: var(--color-fg);
		padding-left: 1.5rem;
		list-style: disc;
		margin: 0 0 1rem;
	}
	.md-view :global(ol) {
		color: var(--color-fg);
		padding-left: 1.5rem;
		list-style: decimal;
		margin: 0 0 1rem;
	}
	.md-view :global(li) { margin-bottom: 0.25rem; }
	.md-view :global(strong) { font-weight: 600; }
	.md-view :global(em) { font-style: italic; }
	.md-view :global(code) {
		background: var(--color-surface-hover, #f3f4f6);
		padding: 1px 4px; border-radius: 3px;
		font-family: ui-monospace, monospace; font-size: 0.92em;
	}
	.md-view :global(pre) {
		background: var(--color-surface-hover, #f3f4f6);
		padding: 10px 12px; border-radius: 6px;
		overflow-x: auto;
	}
	.md-view :global(pre code) {
		background: transparent; padding: 0; border-radius: 0;
	}
	.md-view :global(blockquote) {
		border-left: 3px solid var(--color-border, #d1d5db);
		margin: 1em 0; padding: 0.2em 0.8em;
		color: var(--color-muted, #4b5563);
	}
	.md-view :global(hr) {
		border: 0;
		border-top: 1px solid var(--color-border, #d1d5db);
		margin: 1.5em 0;
	}
	.md-view :global(img) {
		display: block;
		max-width: 100%;
		margin: 1rem 0;
		border: 1px solid var(--color-border);
		border-radius: 8px;
	}
	.md-view :global(a) { color: var(--color-primary, #2563eb); text-decoration: underline; }
	.md-view :global(.md-iris-link) { cursor: pointer; }
	/* Issue #26: text-document refs render in muted colour vs. black diagram refs. */
	.md-view :global(.md-iris-link--text) {
		color: var(--color-muted, #6b7280) !important;
	}
	/* ADR-149: mermaid placeholder + rendered SVG override the
	   :global(pre) code-block styling above so the diagram reads
	   cleanly. */
	.md-view :global(.mermaid-block) {
		background: transparent;
		padding: 0;
		border-radius: 0;
		overflow: visible;
		margin: 1rem 0;
	}
	.md-view :global(.mermaid-block svg) {
		max-width: 100%;
		height: auto;
		display: block;
	}
	.md-view :global(.mermaid-error) {
		border: 1px solid var(--color-danger, #dc2626);
		background: var(--color-surface-hover, #f3f4f6);
		border-radius: 6px;
		padding: 8px 12px;
		margin: 1rem 0;
		color: var(--color-danger, #dc2626);
		font-family: ui-monospace, monospace;
		font-size: 0.92em;
	}
	.md-view :global(.mermaid-error code) {
		background: transparent;
		padding: 0;
	}
</style>
