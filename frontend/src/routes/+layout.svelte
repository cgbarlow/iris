<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import favicon from '$lib/assets/favicon.svg';
	import AppShell from '$lib/components/AppShell.svelte';
	import SessionTimeoutWarning from '$lib/components/SessionTimeoutWarning.svelte';
	import { isAuthenticated } from '$lib/stores/auth.svelte.js';
	import { initViewport } from '$lib/stores/viewport.svelte';
	import { ModeWatcher } from 'mode-watcher';

	let { children } = $props();

	// Wire up the shared viewport breakpoint store once for the whole app
	// (ADR-229). Runs browser-only; returns the matchMedia cleanup.
	$effect(() => initViewport());

	// /login renders without the AppShell (clean full-page login form).
	// Every other route renders inside the AppShell — anonymous visitors
	// get the same shell as authenticated users, just with write UI and
	// admin menu hidden (ADR-123). Admin routes have their own redirect
	// guard in /admin/+layout.svelte.
	const publicRoutes = ['/login'];
	const isPublicRoute = $derived(publicRoutes.includes(page.url.pathname));

	// Open Graph / Twitter metadata lives in src/app.html (ADR-126) —
	// adapter-static ships a single fallback HTML that social scrapers
	// read without running JS, so <svelte:head> tags here wouldn't be
	// visible to them. The tags in app.html are templated at build time
	// via %sveltekit.env.PUBLIC_SITE_URL% and work for every route.
</script>

<ModeWatcher />

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{#if isPublicRoute}
	{@render children()}
{:else}
	<AppShell>
		{@render children()}
	</AppShell>
	{#if isAuthenticated()}
		<SessionTimeoutWarning />
	{/if}
{/if}
