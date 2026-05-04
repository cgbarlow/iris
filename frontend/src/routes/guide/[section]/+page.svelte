<script lang="ts">
	/**
	 * User Guide section page.
	 *
	 * Markdown rendering is delegated to the shared `MarkdownView` component
	 * (introduced for issue #26 / ADR-137). This page now does only:
	 *   - section resolution by slug (with fallback to Getting Started)
	 *   - <svelte:head> title
	 *
	 * The marked + DOMPurify pipeline is no longer duplicated here — see
	 * `$lib/components/MarkdownView.svelte`.
	 */
	import { page } from '$app/state';
	import { GUIDE_BY_SLUG, DEFAULT_SECTION } from '$lib/guide';
	import MarkdownView from '$lib/components/MarkdownView.svelte';

	const section = $derived(
		GUIDE_BY_SLUG[page.params.section] ?? GUIDE_BY_SLUG[DEFAULT_SECTION],
	);
</script>

<svelte:head>
	<title>{section.title} — Iris User Guide</title>
</svelte:head>

<MarkdownView source={section.markdown} />
