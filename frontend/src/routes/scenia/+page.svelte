<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onDestroy } from 'svelte';
	import { isAuthenticated } from '$lib/stores/auth.svelte.js';
	import { getActiveSetId } from '$lib/stores/activeSet.svelte.js';
	import { isSceniaEnabled, SceniaAdapter } from '$lib/scenia/adapter';
	import type { SceniaBulkData } from '$lib/scenia/transforms';

	let mountEl: HTMLDivElement | undefined = $state();
	let unmountFn: (() => void) | null = null;
	let extensionEnabled = $state<boolean | null>(null);
	let error = $state<string | null>(null);
	let mounted = $state(false);

	const setId = $derived(page.url.searchParams.get('setId') ?? getActiveSetId() ?? '');

	$effect(() => {
		if (!isAuthenticated()) {
			goto('/login');
			return;
		}
		checkAndMount();
	});

	async function checkAndMount() {
		extensionEnabled = await isSceniaEnabled();
		if (!extensionEnabled || !mountEl || !setId) return;

		try {
			const { mount } = await import('scenia');
			const adapter = new SceniaAdapter(setId);

			unmountFn = mount({
				container: mountEl,
				dbAdapter: {
					getAppData: () => adapter.getAppData() as Promise<any>,
					saveAppData: (data: any) => adapter.saveAppData(data).then(() => {}),
					getAllVersions: () => Promise.resolve([]),
					saveVersion: () => Promise.resolve(),
					deleteVersion: () => Promise.resolve(),
				},
				onNavigateExternal: (url: string) => goto(url),
			});
			mounted = true;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load Scenia';
			console.error('Scenia mount error:', e);
		}
	}

	onDestroy(() => {
		unmountFn?.();
	});
</script>

<svelte:head>
	<title>Scenia — Iris</title>
</svelte:head>

{#if extensionEnabled === false}
	<div class="flex flex-col items-center justify-center gap-4 py-20">
		<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Scenia Roadmapping</h1>
		<p style="color: var(--color-muted)">The Scenia extension is not installed.</p>
		<a
			href="/admin/settings/extensions"
			class="rounded px-4 py-2 text-sm font-medium text-white"
			style="background-color: var(--color-primary)"
		>
			Install Extension
		</a>
	</div>
{:else if extensionEnabled === null}
	<p style="color: var(--color-muted)">Loading Scenia...</p>
{:else if error}
	<div
		class="m-4 rounded border p-4"
		style="border-color: var(--color-danger); color: var(--color-danger)"
	>
		{error}
	</div>
{:else if !setId}
	<div class="flex flex-col items-center justify-center gap-4 py-20">
		<p style="color: var(--color-muted)">Select a set first, then open Scenia.</p>
		<a
			href="/roadmap"
			class="rounded px-4 py-2 text-sm font-medium text-white"
			style="background-color: var(--color-primary)"
		>
			Go to Roadmap
		</a>
	</div>
{/if}

<div
	bind:this={mountEl}
	class="scenia-container"
	style="min-height: calc(100vh - 3.5rem); {mounted ? '' : 'display: none;'}"
></div>

<style>
	.scenia-container {
		width: 100%;
	}
</style>
