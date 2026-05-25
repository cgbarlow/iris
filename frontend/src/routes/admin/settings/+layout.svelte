<script lang="ts">
	import { page } from '$app/state';

	let { children } = $props();

	const tabs = [
		{ href: '/admin/settings', label: 'General' },
		{ href: '/admin/settings/themes', label: 'Themes' },
		{ href: '/admin/settings/ai', label: 'AI' },
		{ href: '/admin/settings/extensions', label: 'Extensions' },
		{ href: '/admin/settings/aggregation-profiles', label: 'Aggregation' },
	];

	const activeTab = $derived(
		tabs.findLast((t) => page.url.pathname.startsWith(t.href)) ?? tabs[0]
	);
</script>

<svelte:head>
	<title>Settings — Iris Admin</title>
</svelte:head>

<nav aria-label="Breadcrumb" class="mb-4 text-sm" style="color: var(--color-muted)">
	<ol class="flex gap-1">
		<li><a href="/admin" style="color: var(--color-primary)">Admin</a></li>
		<li aria-hidden="true">/</li>
		<li aria-current="page">Settings</li>
	</ol>
</nav>

<h1 class="mb-4 text-2xl font-bold" style="color: var(--color-fg)">Settings</h1>

<div class="mb-6 flex gap-0 border-b" style="border-color: var(--color-border)">
	{#each tabs as tab}
		<a
			href={tab.href}
			class="px-5 py-2 text-sm font-medium transition-colors"
			style="color: {activeTab.href === tab.href ? 'var(--color-primary)' : 'var(--color-muted)'}; border-bottom: 2px solid {activeTab.href === tab.href ? 'var(--color-primary)' : 'transparent'}; margin-bottom: -1px"
			aria-current={activeTab.href === tab.href ? 'page' : undefined}
		>
			{tab.label}
		</a>
	{/each}
</div>

{@render children()}
