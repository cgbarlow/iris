<script lang="ts">
	import { page } from '$app/state';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import { GUIDE_BY_SLUG, DEFAULT_SECTION } from '$lib/guide';

	// Resolve section by slug; fall back to Getting Started if the URL
	// points at a section that doesn't exist rather than 404'ing.
	const section = $derived(
		GUIDE_BY_SLUG[page.params.section] ?? GUIDE_BY_SLUG[DEFAULT_SECTION],
	);

	// Render markdown through DOMPurify before {@html} per protocol #7.
	// `marked.parse` is sync when given a string with async: false (default).
	const html = $derived(
		DOMPurify.sanitize(marked.parse(section.markdown) as string),
	);
</script>

<svelte:head>
	<title>{section.title} — Iris User Guide</title>
</svelte:head>

<!-- Content is Iris-controlled markdown sanitised via DOMPurify (protocol #7). -->
<!-- eslint-disable-next-line svelte/no-at-html-tags -->
{@html html}
