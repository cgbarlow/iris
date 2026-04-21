<script lang="ts">
	import { goto } from '$app/navigation';
	import { isAuthenticated } from '$lib/stores/auth.svelte.js';
	import { onMount } from 'svelte';

	let { children } = $props();

	// Admin routes stay behind auth (ADR-123). Root +layout no longer
	// redirects unauthenticated users; this admin-scoped layout does,
	// so /admin/* remains private even though the rest of the app is
	// anonymously readable.
	onMount(() => {
		if (!isAuthenticated()) {
			goto('/login');
		}
	});
</script>

{#if isAuthenticated()}
	{@render children()}
{/if}
