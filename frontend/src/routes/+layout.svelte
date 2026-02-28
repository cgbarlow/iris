<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import favicon from '$lib/assets/favicon.svg';
	import AppShell from '$lib/components/AppShell.svelte';
	import SessionTimeoutWarning from '$lib/components/SessionTimeoutWarning.svelte';
	import { isAuthenticated } from '$lib/stores/auth.svelte.js';
	import { ModeWatcher } from 'mode-watcher';
	import { tick } from 'svelte';

	let { children } = $props();

	const publicRoutes = ['/login'];
	const isPublicRoute = $derived(publicRoutes.includes(page.url.pathname));

	$effect(() => {
		if (!isPublicRoute && !isAuthenticated()) {
			tick().then(() => {
				if (!isAuthenticated()) {
					goto('/login');
				}
			});
		}
	});
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
