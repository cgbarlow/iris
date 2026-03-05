<script lang="ts">
	import { mode, setMode } from 'mode-watcher';
	import { onMount } from 'svelte';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import { getDefaultNotation, setDefaultNotation } from '$lib/stores/defaultNotation.svelte';

	let highContrast = $state(false);
	let isSystem = $state(false);
	let defaultNotation = $state('simple');

	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let passwordError = $state('');
	let passwordSuccess = $state('');
	let passwordLoading = $state(false);

	onMount(() => {
		highContrast = localStorage.getItem('iris-high-contrast') === 'true';
		isSystem = localStorage.getItem('iris-theme') === 'system';
		defaultNotation = getDefaultNotation();
		if (highContrast) {
			document.documentElement.classList.add('high-contrast');
		}
	});

	function selectNotation(value: string) {
		defaultNotation = value;
		setDefaultNotation(value);
	}


	const currentTheme = $derived(
		highContrast ? 'high-contrast' : isSystem ? 'system' : (mode.current ?? 'light'),
	);

	function selectTheme(theme: string) {
		highContrast = false;
		isSystem = false;
		document.documentElement.classList.remove('high-contrast');
		localStorage.setItem('iris-high-contrast', 'false');

		if (theme === 'system') {
			isSystem = true;
			localStorage.setItem('iris-theme', 'system');
			setMode('system');
		} else if (theme === 'high-contrast') {
			highContrast = true;
			document.documentElement.classList.add('high-contrast');
			localStorage.setItem('iris-high-contrast', 'true');
			localStorage.setItem('iris-theme', 'high-contrast');
			setMode('dark');
		} else {
			localStorage.setItem('iris-theme', theme);
			setMode(theme as 'light' | 'dark');
		}
	}

	async function handlePasswordChange(event: SubmitEvent) {
		event.preventDefault();
		passwordError = '';
		passwordSuccess = '';

		if (newPassword !== confirmPassword) {
			passwordError = 'New passwords do not match.';
			return;
		}

		if (newPassword.length < 12) {
			passwordError = 'New password must be at least 12 characters long.';
			return;
		}

		passwordLoading = true;
		try {
			await apiFetch('/api/auth/change-password', {
				method: 'POST',
				body: JSON.stringify({
					current_password: currentPassword,
					new_password: newPassword,
				}),
			});
			passwordSuccess = 'Password changed successfully.';
			currentPassword = '';
			newPassword = '';
			confirmPassword = '';
		} catch (err) {
			if (err instanceof ApiError) {
				passwordError = err.message;
			} else {
				passwordError = 'An unexpected error occurred.';
			}
		} finally {
			passwordLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Settings — Iris</title>
</svelte:head>

<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Settings</h1>
<p class="mt-2" style="color: var(--color-muted)">Configure your preferences.</p>

<section class="mt-6">
	<div>
		<label for="settings-theme" class="text-lg font-semibold" style="color: var(--color-fg)">Theme</label>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">Choose your preferred colour scheme.</p>
		<select
			id="settings-theme"
			value={currentTheme}
			onchange={(e) => selectTheme((e.target as HTMLSelectElement).value)}
			class="mt-2 w-full rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		>
			<option value="system">System — follows your operating system preference</option>
			<option value="light">Light — light background with dark text</option>
			<option value="dark">Dark — dark background with light text</option>
			<option value="high-contrast">High Contrast — maximum contrast for accessibility</option>
		</select>
	</div>
</section>

<section class="mt-6">
	<div>
		<label for="settings-notation" class="text-lg font-semibold" style="color: var(--color-fg)">Default Notation</label>
		<p class="mt-1 text-sm" style="color: var(--color-muted)">Choose your preferred default notation for new diagrams and elements.</p>
		<select
			id="settings-notation"
			value={defaultNotation}
			onchange={(e) => selectNotation((e.target as HTMLSelectElement).value)}
			class="mt-2 w-full rounded border px-3 py-2 text-sm"
			style="border-color: var(--color-border); background: var(--color-bg); color: var(--color-fg)"
		>
			<option value="simple">Simple — basic shapes (component, service, interface, actor, database)</option>
			<option value="uml">UML — class, object, use case, state, activity</option>
			<option value="archimate">ArchiMate — business, application, technology layers</option>
			<option value="c4">C4 — person, software system, container, component</option>
		</select>
	</div>
</section>

<section class="mt-6">
	<h2 class="text-lg font-semibold" style="color: var(--color-fg)">Change Password</h2>
	<p class="mt-1 text-sm" style="color: var(--color-muted)">Update your account password.</p>

	<form class="mt-4 flex flex-col gap-4" onsubmit={handlePasswordChange}>
		{#if passwordError}
			<p role="alert" class="text-sm rounded border px-4 py-2" style="color: var(--color-error); border-color: var(--color-error); background-color: var(--color-bg)">
				{passwordError}
			</p>
		{/if}

		{#if passwordSuccess}
			<p role="alert" class="text-sm rounded border px-4 py-2" style="color: var(--color-success); border-color: var(--color-success); background-color: var(--color-bg)">
				{passwordSuccess}
			</p>
		{/if}

		<label class="flex flex-col gap-1">
			<span class="text-sm" style="color: var(--color-fg)">Current Password</span>
			<input
				type="password"
				autocomplete="current-password"
				bind:value={currentPassword}
				required
				class="rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background-color: var(--color-bg); color: var(--color-fg)"
			/>
		</label>

		<label class="flex flex-col gap-1">
			<span class="text-sm" style="color: var(--color-fg)">New Password</span>
			<input
				type="password"
				autocomplete="new-password"
				bind:value={newPassword}
				required
				class="rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background-color: var(--color-bg); color: var(--color-fg)"
			/>
		</label>

		<label class="flex flex-col gap-1">
			<span class="text-sm" style="color: var(--color-fg)">Confirm Password</span>
			<input
				type="password"
				autocomplete="new-password"
				bind:value={confirmPassword}
				required
				class="rounded border px-3 py-2 text-sm"
				style="border-color: var(--color-border); background-color: var(--color-bg); color: var(--color-fg)"
			/>
		</label>

		<button
			type="submit"
			disabled={passwordLoading}
			class="self-start rounded px-4 py-2 text-sm text-white"
			style="background-color: var(--color-primary); opacity: {passwordLoading ? '0.6' : '1'}; cursor: {passwordLoading ? 'not-allowed' : 'pointer'}"
		>
			{passwordLoading ? 'Changing...' : 'Change Password'}
		</button>
	</form>
</section>
