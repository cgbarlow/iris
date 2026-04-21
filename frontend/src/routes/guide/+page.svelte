<script lang="ts">
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { DEFAULT_SECTION } from '$lib/guide';

	// /guide root redirects to the first section so a direct visit to
	// /guide always lands on content rather than an empty page.
	onMount(() => {
		goto(`/guide/${DEFAULT_SECTION}`, { replaceState: true });
	});
</script>

<svelte:head>
	<title>User Guide — Iris</title>
</svelte:head>
