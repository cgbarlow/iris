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
		checklistItemStates,
		decorateChecklist,
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
		/** Issue #255 / ADR-239: when true, list items render as interactive
		 *  (tappable) checkboxes. Strictly opt-in — defaults off so the User
		 *  Guide (the other MarkdownView consumer) is unaffected. */
		checklist?: boolean;
		/** Called when a checklist item is tapped, with its 0-based
		 *  document-order index. The caller flips the source marker + saves. */
		ontoggle?: (index: number) => void;
	}

	let { source, textDiagramIds, onheadings, onlinks, checklist = false, ontoggle }: Props = $props();

	const rendered = $derived(renderMarkdown(source, textDiagramIds));
	const html = $derived(rendered.html);
	const headings = $derived(extractHeadings(source));

	$effect(() => { onheadings?.(headings); });
	$effect(() => { onlinks?.(rendered.links); });

	function onClick(e: MouseEvent) {
		// ADR-239: a checklist checkbox tap toggles the item. Mutually
		// exclusive with the iris-link branch below (different targets).
		const check = (e.target as HTMLElement | null)?.closest('.md-check');
		if (check && checklist) {
			const idx = Number(check.getAttribute('data-checklist-index'));
			if (!Number.isNaN(idx)) {
				e.preventDefault();
				ontoggle?.(idx);
			}
			return;
		}
		const t = (e.target as HTMLElement | null)?.closest('a.md-iris-link');
		if (!t) return;
		const kind = t.getAttribute('data-iris-kind');
		const id = t.getAttribute('data-iris-id');
		if (!kind || !id) return;
		e.preventDefault();
		// ADR-209 (v6.17.0): route all five entity kinds. Default falls
		// back to elements/<id> to keep legacy behaviour for any link
		// not yet recognised.
		let path: string;
		if (kind === 'diagram') path = `/views/${id}`;
		else if (kind === 'set') path = `/sets/${id}`;
		else if (kind === 'package') path = `/packages/${id}`;
		else if (kind === 'collection') path = `/collections/${id}`;
		else path = `/elements/${id}`;
		// v6.37.3: preserve `?focus=1` when jumping from one focused view
		// to another. Only forward to diagram links — other entity routes
		// don't have a focus concept.
		if (kind === 'diagram' && typeof window !== 'undefined') {
			const sp = new URLSearchParams(window.location.search);
			if (sp.get('focus') === '1') path += '?focus=1';
		}
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

	// ADR-239: decorate list items as interactive checkboxes when checklist
	// mode is on. Re-runs whenever {@html} replaces the content (html change)
	// or the mode flips. Checked-state is derived from the source markers
	// (the render pipeline strips marked's <input>, and the markers survive
	// Smart Markdown token resolution so the index mapping holds).
	$effect(() => {
		void html;
		if (!rootEl) return;
		if (checklist) decorateChecklist(rootEl, checklistItemStates(source));
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
	/* ADR-239: checklist mode. Items carrying a .md-check button drop their
	   bullet and gain a tappable square that strikes the item when checked. */
	.md-view :global(li:has(.md-check)) {
		list-style: none;
		margin-left: -1.1rem;
		display: flex;
		align-items: flex-start;
		gap: 0.5rem;
	}
	.md-view :global(.md-check) {
		flex: 0 0 auto;
		width: 1.05em;
		height: 1.05em;
		margin-top: 0.15em;
		padding: 0;
		border: 1.5px solid var(--color-border, #9ca3af);
		border-radius: 4px;
		background: var(--color-surface, #fff);
		cursor: pointer;
		line-height: 1;
		position: relative;
	}
	.md-view :global(.md-check[aria-checked='true']) {
		background: var(--color-primary, #2563eb);
		border-color: var(--color-primary, #2563eb);
	}
	.md-view :global(.md-check[aria-checked='true'])::after {
		content: '';
		position: absolute;
		left: 0.3em;
		top: 0.08em;
		width: 0.28em;
		height: 0.55em;
		border: solid #fff;
		border-width: 0 2px 2px 0;
		transform: rotate(45deg);
	}
	.md-view :global(li.md-check-checked) {
		text-decoration: line-through;
		color: var(--color-muted, #6b7280);
	}
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
