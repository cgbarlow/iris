<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { isAuthenticated, getCurrentUser, clearAuth } from '$lib/stores/auth.svelte.js';
	import { getActiveSetId, getActiveSetName } from '$lib/stores/activeSet.svelte.js';
	import { apiFetch } from '$lib/utils/api';

	let { children } = $props();

	let sidebarOpen = $state(true);
	let recycleBinCount = $state(0);

	async function loadRecycleBinCount() {
		try {
			const data = await apiFetch<{ total: number }>('/api/recycle-bin?page=1&page_size=1');
			recycleBinCount = data.total;
		} catch {
			recycleBinCount = 0;
		}
	}

	$effect(() => {
		// Re-check on auth state and page navigation
		void page.url.pathname;
		if (isAuthenticated()) {
			loadRecycleBinCount();
		}
	});

	const activeSetId = $derived(getActiveSetId());
	const activeSetName = $derived(getActiveSetName());

	const navItems = [
		{ href: '/', label: 'Dashboard', shortcut: 'H', icon: 'dashboard' },
		{ href: '/sets', label: 'Sets', shortcut: 'T', icon: 'sets' },
		{ href: '/diagrams', label: 'Diagrams', shortcut: 'M', icon: 'diagrams' },
		{ href: '/elements', label: 'Elements', shortcut: 'E', icon: 'elements' },
		{ href: '/bookmarks', label: 'Bookmarks', shortcut: 'B', icon: 'bookmarks' },
		{ href: '/import', label: 'Import', shortcut: 'I', icon: 'import' },
		{ href: '/recycle-bin', label: 'Recycle Bin', shortcut: 'R', icon: 'recycle-bin' },
		{ href: '/settings', label: 'Settings', shortcut: 'S', icon: 'settings' },
	];

	const adminItems = [
		{ href: '/admin/users', label: 'Users', shortcut: 'U', icon: 'users' },
		{ href: '/admin/audit', label: 'Audit Log', shortcut: 'A', icon: 'audit' },
		{ href: '/admin/locks', label: 'Locks', shortcut: 'L', icon: 'lock' },
		{ href: '/admin/settings', label: 'Settings', shortcut: 'S', icon: 'admin-settings' },
	];

	async function handleLogout() {
		clearAuth();
		await goto('/login');
	}
</script>

<!-- Phosphor-style SVG icon paths (256x256 viewBox, fill="currentColor") -->
{#snippet navIcon(icon: string)}
	<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" fill="currentColor" width="16" height="16" aria-hidden="true" style="flex-shrink: 0">
		{#if icon === 'dashboard'}
			<path d="M216,40H40A16,16,0,0,0,24,56V200a16,16,0,0,0,16,16H216a16,16,0,0,0,16-16V56A16,16,0,0,0,216,40Zm0,16V96H40V56ZM40,200V112H120V200Zm96,0V112h80v88Z"/>
		{:else if icon === 'sets'}
			<path d="M224,48H160a40,40,0,0,0-32,16A40,40,0,0,0,96,48H32A16,16,0,0,0,16,64V192a16,16,0,0,0,16,16H96a24,24,0,0,1,24,24,8,8,0,0,0,16,0,24,24,0,0,1,24-24h64a16,16,0,0,0,16-16V64A16,16,0,0,0,224,48ZM96,192H32V64H96a24,24,0,0,1,24,24V200A39.81,39.81,0,0,0,96,192Zm128,0H160a39.81,39.81,0,0,0-24,8V88a24,24,0,0,1,24-24h64Z"/>
		{:else if icon === 'diagrams'}
			<path d="M176,152h32a16,16,0,0,0,16-16V104a16,16,0,0,0-16-16H176a16,16,0,0,0-16,16v8H88V80h8a16,16,0,0,0,16-16V32A16,16,0,0,0,96,16H64A16,16,0,0,0,48,32V64A16,16,0,0,0,64,80h8V192a24,24,0,0,0,24,24h64v8a16,16,0,0,0,16,16h32a16,16,0,0,0,16-16V192a16,16,0,0,0-16-16H176a16,16,0,0,0-16,16v8H96a8,8,0,0,1-8-8V128h72v8A16,16,0,0,0,176,152ZM64,32H96V64H64ZM176,192h32v32H176Zm0-88h32v32H176Z"/>
		{:else if icon === 'elements'}
			<path d="M223.68,66.15,135.68,18a15.88,15.88,0,0,0-15.36,0l-88,48.17a16,16,0,0,0-8.32,14v95.64a16,16,0,0,0,8.32,14l88,48.17a15.88,15.88,0,0,0,15.36,0l88-48.17a16,16,0,0,0,8.32-14V80.18A16,16,0,0,0,223.68,66.15ZM128,32l80.34,44L128,120,47.66,76ZM40,90l80,43.78v85.79L40,175.82Zm96,129.57V133.82L216,90v85.78Z"/>
		{:else if icon === 'import'}
			<path d="M224,152v56a16,16,0,0,1-16,16H48a16,16,0,0,1-16-16V152a8,8,0,0,1,16,0v56H208V152a8,8,0,0,1,16,0Zm-101.66,5.66a8,8,0,0,0,11.32,0l40-40a8,8,0,0,0-11.32-11.32L136,132.69V40a8,8,0,0,0-16,0v92.69L93.66,106.34a8,8,0,0,0-11.32,11.32Z"/>
		{:else if icon === 'bookmarks'}
			<path d="M184,32H72A16,16,0,0,0,56,48V224a8,8,0,0,0,12.24,6.78L128,193.43l59.77,37.35A8,8,0,0,0,200,224V48A16,16,0,0,0,184,32Zm0,177.57-51.77-32.35a8,8,0,0,0-8.48,0L72,209.57V48H184Z"/>
		{:else if icon === 'recycle-bin'}
			<path d="M216,48H176V40a24,24,0,0,0-24-24H104A24,24,0,0,0,80,40v8H40a8,8,0,0,0,0,16h8V208a16,16,0,0,0,16,16H192a16,16,0,0,0,16-16V64h8a8,8,0,0,0,0-16ZM96,40a8,8,0,0,1,8-8h48a8,8,0,0,1,8,8v8H96Zm96,168H64V64H192ZM112,104v64a8,8,0,0,1-16,0V104a8,8,0,0,1,16,0Zm48,0v64a8,8,0,0,1-16,0V104a8,8,0,0,1,16,0Z"/>
		{:else if icon === 'settings'}
			<path d="M40,88H73a32,32,0,0,0,62,0h81a8,8,0,0,0,0-16H135a32,32,0,0,0-62,0H40a8,8,0,0,0,0,16Zm64-24a16,16,0,1,1-16,16A16,16,0,0,1,104,64ZM216,168H199a32,32,0,0,0-62,0H40a8,8,0,0,0,0,16h97a32,32,0,0,0,62,0h17a8,8,0,0,0,0-16Zm-48,24a16,16,0,1,1,16-16A16,16,0,0,1,168,192Z"/>
		{:else if icon === 'users'}
			<path d="M117.25,157.92a60,60,0,1,0-66.5,0A95.83,95.83,0,0,0,3.53,195.63a8,8,0,1,0,13.4,8.74,80,80,0,0,1,134.14,0,8,8,0,0,0,13.4-8.74A95.83,95.83,0,0,0,117.25,157.92ZM40,108a44,44,0,1,1,44,44A44.05,44.05,0,0,1,40,108Zm210.14,98.7a8,8,0,0,1-11.07-2.33A79.83,79.83,0,0,0,172,168a8,8,0,0,1,0-16,44,44,0,1,0-16.34-84.87,8,8,0,1,1-5.94-14.85,60,60,0,0,1,55.53,105.64,95.83,95.83,0,0,1,47.22,37.71A8,8,0,0,1,250.14,206.7Z"/>
		{:else if icon === 'audit'}
			<path d="M213.66,82.34l-56-56A8,8,0,0,0,152,24H56A16,16,0,0,0,40,40V216a16,16,0,0,0,16,16H200a16,16,0,0,0,16-16V88A8,8,0,0,0,213.66,82.34ZM160,51.31,188.69,80H160ZM200,216H56V40h88V88a8,8,0,0,0,8,8h48V216Zm-32-80a8,8,0,0,1-8,8H96a8,8,0,0,1,0-16h64A8,8,0,0,1,168,136Zm0,32a8,8,0,0,1-8,8H96a8,8,0,0,1,0-16h64A8,8,0,0,1,168,168Z"/>
		{:else if icon === 'admin-settings'}
			<path d="M40,88H73a32,32,0,0,0,62,0h81a8,8,0,0,0,0-16H135a32,32,0,0,0-62,0H40a8,8,0,0,0,0,16Zm64-24a16,16,0,1,1-16,16A16,16,0,0,1,104,64ZM216,168H199a32,32,0,0,0-62,0H40a8,8,0,0,0,0,16h97a32,32,0,0,0,62,0h17a8,8,0,0,0,0-16Zm-48,24a16,16,0,1,1,16-16A16,16,0,0,1,168,192Z"/>
		{:else if icon === 'lock'}
			<path d="M208,80H176V56a48,48,0,0,0-96,0V80H48A16,16,0,0,0,32,96V208a16,16,0,0,0,16,16H208a16,16,0,0,0,16-16V96A16,16,0,0,0,208,80ZM96,56a32,32,0,0,1,64,0V80H96ZM208,208H48V96H208V208Zm-80-36V140a12,12,0,1,1,0-24,12,12,0,0,1,12,12,12,12,0,0,1-12,12v32a8,8,0,0,1-16,0Z"/>
		{/if}
	</svg>
{/snippet}

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
			{#if activeSetId}
				<span style="color: var(--color-fg)">/</span>
				<a href="/sets" class="text-lg" style="color: var(--color-fg)">{activeSetName}</a>
			{/if}
		</div>

		<div class="flex items-center gap-4">
			<a
				href="/help"
				class="header-link rounded px-3 py-1 text-sm transition-colors"
				style="color: var(--color-fg)"
			>
				Help
			</a>
			{#if isAuthenticated()}
				<button
					onclick={handleLogout}
					class="header-link rounded px-3 py-1 text-sm transition-colors"
					style="color: var(--color-danger)"
				>
					Sign out ({getCurrentUser()?.username})
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
								class="sidebar-link flex items-center gap-2.5 rounded px-3 py-2 text-sm transition-colors"
								style="color: var(--color-fg){(item.href === '/' ? page.url.pathname === '/' : page.url.pathname.startsWith(item.href)) ? '; background-color: var(--color-bg)' : ''}"
								aria-current={(item.href === '/' ? page.url.pathname === '/' : page.url.pathname.startsWith(item.href)) ? 'page' : undefined}
								title="{item.label} ({item.shortcut})"
							>
								{@render navIcon(item.icon)}
								{item.label}
								{#if item.icon === 'recycle-bin' && recycleBinCount > 0}
									<span
										class="recycle-bin-indicator"
										aria-label="{recycleBinCount} item{recycleBinCount === 1 ? '' : 's'} in recycle bin"
									></span>
								{/if}
							</a>
						</li>
					{/each}
				</ul>

				{#if getCurrentUser()?.role === 'admin'}
					<div class="mt-4 border-t pt-4" style="border-color: var(--color-border)">
						<h2 class="mb-2 px-3 text-xs font-semibold uppercase" style="color: var(--color-muted)">
							Admin
						</h2>
						<ul class="space-y-1">
							{#each adminItems as item}
								<li>
									<a
										href={item.href}
										class="sidebar-link flex items-center gap-2.5 rounded px-3 py-2 text-sm transition-colors"
										style="color: var(--color-fg){page.url.pathname === item.href ? '; background-color: var(--color-bg)' : ''}"
										aria-current={page.url.pathname === item.href ? 'page' : undefined}
										title="{item.label} ({item.shortcut})"
									>
										{@render navIcon(item.icon)}
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
	.sidebar-link:hover,
	.header-link:hover {
		background-color: var(--color-bg);
	}
	.recycle-bin-indicator {
		display: inline-block;
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background-color: var(--color-primary);
		flex-shrink: 0;
	}
</style>
