<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { isAuthenticated, getCurrentUser, clearAuth } from '$lib/stores/auth.svelte.js';

	let { children } = $props();

	let sidebarOpen = $state(true);

	const navItems = [
		{ href: '/', label: 'Dashboard', shortcut: 'H' },
		{ href: '/models', label: 'Models', shortcut: 'M' },
		{ href: '/entities', label: 'Entities', shortcut: 'E' },
		{ href: '/bookmarks', label: 'Bookmarks', shortcut: 'B' },
		{ href: '/settings', label: 'Settings', shortcut: 'S' },
	];

	const adminItems = [
		{ href: '/admin/users', label: 'Users', shortcut: 'U' },
		{ href: '/admin/audit', label: 'Audit Log', shortcut: 'A' },
	];

	async function handleLogout() {
		clearAuth();
		await goto('/login');
	}
</script>

<div class="flex min-h-screen flex-col">
	<!-- Skip link per WCAG 2.4.1 -->
	<a href="#main-content" class="skip-link">Skip to main content</a>

	<!-- Header / Banner landmark -->
	<header
		class="flex h-14 items-center justify-between border-b px-4"
		style="background-color: var(--color-surface); border-color: var(--color-border)"
	>
		<div class="flex items-center gap-3">
			<button
				onclick={() => (sidebarOpen = !sidebarOpen)}
				aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
				class="rounded p-1"
			>
				<span aria-hidden="true" class="text-lg">&#9776;</span>
			</button>
			<a href="/" class="text-lg font-bold" style="color: var(--color-fg)">Iris</a>
		</div>

		<div class="flex items-center gap-4">
			<a
				href="/help"
				class="rounded px-2 py-1 text-sm"
				style="color: var(--color-muted)"
				aria-label="Help"
			>
				Help
			</a>
			{#if isAuthenticated()}
				<span class="text-sm" style="color: var(--color-muted)">
					{getCurrentUser()?.username}
				</span>
				<button
					onclick={handleLogout}
					class="rounded px-3 py-1 text-sm"
					style="color: var(--color-danger)"
				>
					Sign out
				</button>
			{/if}
		</div>
	</header>

	<div class="flex flex-1">
		<!-- Sidebar / Navigation landmark -->
		{#if sidebarOpen}
			<nav
				aria-label="Main navigation"
				class="w-56 border-r p-4"
				style="background-color: var(--color-surface); border-color: var(--color-border)"
			>
				<ul class="space-y-1">
					{#each navItems as item}
						<li>
							<a
								href={item.href}
								class="sidebar-link block rounded px-3 py-2 text-sm transition-colors"
								style="color: var(--color-fg){page.url.pathname === item.href ? '; background-color: var(--color-bg)' : ''}"
								aria-current={page.url.pathname === item.href ? 'page' : undefined}
								title="{item.label} ({item.shortcut})"
							>
								{item.label}
							</a>
						</li>
					{/each}
				</ul>

				{#if getCurrentUser()?.role === 'admin'}
					<div class="mt-6">
						<h2 class="mb-2 px-3 text-xs font-semibold uppercase" style="color: var(--color-muted)">
							Admin
						</h2>
						<ul class="space-y-1">
							{#each adminItems as item}
								<li>
									<a
										href={item.href}
										class="sidebar-link block rounded px-3 py-2 text-sm transition-colors"
										style="color: var(--color-fg){page.url.pathname === item.href ? '; background-color: var(--color-bg)' : ''}"
										aria-current={page.url.pathname === item.href ? 'page' : undefined}
										title="{item.label} ({item.shortcut})"
									>
										{item.label}
									</a>
								</li>
							{/each}
						</ul>
					</div>
				{/if}
			</nav>
		{/if}

		<!-- Main content landmark -->
		<main id="main-content" class="flex-1 p-6" tabindex="-1">
			{@render children()}
		</main>
	</div>
</div>

<style>
	.sidebar-link:hover {
		background-color: var(--color-bg);
	}
</style>
