<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import favicon from '$lib/assets/favicon.svg';
	import AppShell from '$lib/components/AppShell.svelte';
	import SessionTimeoutWarning from '$lib/components/SessionTimeoutWarning.svelte';
	import { isAuthenticated } from '$lib/stores/auth.svelte.js';
	import { ModeWatcher } from 'mode-watcher';

	let { children } = $props();

	const publicRoutes = ['/login'];
	const isPublicRoute = $derived(publicRoutes.includes(page.url.pathname));
</script>

<ModeWatcher />

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{#if isPublicRoute || !isAuthenticated()}
	{@render children()}
{:else}
	<AppShell>
		{@render children()}
	</AppShell>
	<SessionTimeoutWarning />
{/if}
