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
		const path = kind === 'diagram' ? `/diagrams/${id}` : `/elements/${id}`;
		goto(path);
	}

	onMount(() => {
		// Headings/links are emitted via queueMicrotask after the first $derived run.
		void headings;
		void html;
	});
</script>

<div class="md-view" onclick={onClick} role="presentation">
	<!-- Sanitised markdown — pipeline above enforces protocol #7. -->
	<!-- eslint-disable-next-line svelte/no-at-html-tags -->
	{@html html}
</div>

<style>
	.md-view :global(h1), .md-view :global(h2), .md-view :global(h3),
	.md-view :global(h4), .md-view :global(h5), .md-view :global(h6) {
		margin: 1.4em 0 0.6em;
		line-height: 1.25;
	}
	.md-view :global(p)   { margin: 0.6em 0; line-height: 1.55; }
	.md-view :global(ul), .md-view :global(ol) { margin: 0.6em 0; padding-left: 1.5em; }
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
	.md-view :global(blockquote) {
		border-left: 3px solid var(--color-border, #d1d5db);
		margin: 1em 0; padding: 0.2em 0.8em;
		color: var(--color-muted, #4b5563);
	}
	.md-view :global(a) { color: var(--color-primary, #2563eb); text-decoration: underline; }
	.md-view :global(.md-iris-link) { cursor: pointer; }
	/* Issue #26: text-document refs render in muted colour vs. black diagram refs. */
	.md-view :global(.md-iris-link--text) {
		color: var(--color-muted, #6b7280) !important;
	}
</style>
