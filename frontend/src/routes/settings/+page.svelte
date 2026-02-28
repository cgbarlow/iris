<script lang="ts">
	import { mode, setMode } from 'mode-watcher';
	import { onMount } from 'svelte';
	import { apiFetch, ApiError } from '$lib/utils/api';

	let highContrast = $state(false);
	let isSystem = $state(false);

	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmPassword = $state('');
	let passwordError = $state('');
	let passwordSuccess = $state('');
	let passwordLoading = $state(false);

	onMount(() => {
		highContrast = localStorage.getItem('iris-high-contrast') === 'true';
		isSystem = localStorage.getItem('iris-theme') === 'system';
		if (highContrast) {
			document.documentElement.classList.add('high-contrast');
		}
	});

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
	<h2 class="text-lg font-semibold" style="color: var(--color-fg)">Theme</h2>
	<p class="mt-1 text-sm" style="color: var(--color-muted)">Choose your preferred colour scheme.</p>

	<fieldset class="mt-4 flex flex-col gap-3" role="radiogroup" aria-label="Theme selection">
		<label
			class="flex items-center gap-3 rounded border px-4 py-3 cursor-pointer"
			style="border-color: {currentTheme === 'system' ? 'var(--color-primary)' : 'var(--color-border)'}; background-color: {currentTheme === 'system' ? 'var(--color-bg)' : 'transparent'}"
		>
			<input
				type="radio"
				name="theme"
				value="system"
				checked={currentTheme === 'system'}
				onchange={() => selectTheme('system')}
				class="accent-[var(--color-primary)]"
			/>
			<div>
				<span style="color: var(--color-fg)">System</span>
				<p class="text-xs" style="color: var(--color-muted)">Follows your operating system preference</p>
			</div>
		</label>

		<label
			class="flex items-center gap-3 rounded border px-4 py-3 cursor-pointer"
			style="border-color: {currentTheme === 'light' ? 'var(--color-primary)' : 'var(--color-border)'}; background-color: {currentTheme === 'light' ? 'var(--color-bg)' : 'transparent'}"
		>
			<input
				type="radio"
				name="theme"
				value="light"
				checked={currentTheme === 'light'}
				onchange={() => selectTheme('light')}
				class="accent-[var(--color-primary)]"
			/>
			<span style="color: var(--color-fg)">Light</span>
		</label>

		<label
			class="flex items-center gap-3 rounded border px-4 py-3 cursor-pointer"
			style="border-color: {currentTheme === 'dark' ? 'var(--color-primary)' : 'var(--color-border)'}; background-color: {currentTheme === 'dark' ? 'var(--color-bg)' : 'transparent'}"
		>
			<input
				type="radio"
				name="theme"
				value="dark"
				checked={currentTheme === 'dark'}
				onchange={() => selectTheme('dark')}
				class="accent-[var(--color-primary)]"
			/>
			<span style="color: var(--color-fg)">Dark</span>
		</label>

		<label
			class="flex items-center gap-3 rounded border px-4 py-3 cursor-pointer"
			style="border-color: {currentTheme === 'high-contrast' ? 'var(--color-primary)' : 'var(--color-border)'}; background-color: {currentTheme === 'high-contrast' ? 'var(--color-bg)' : 'transparent'}"
		>
			<input
				type="radio"
				name="theme"
				value="high-contrast"
				checked={currentTheme === 'high-contrast'}
				onchange={() => selectTheme('high-contrast')}
				class="accent-[var(--color-primary)]"
			/>
			<span style="color: var(--color-fg)">High Contrast</span>
		</label>
	</fieldset>
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
			class="self-start rounded px-4 py-2 text-sm font-medium"
			style="background-color: var(--color-primary); color: var(--color-primary-fg); opacity: {passwordLoading ? '0.6' : '1'}; cursor: {passwordLoading ? 'not-allowed' : 'pointer'}"
		>
			{passwordLoading ? 'Changing...' : 'Change Password'}
		</button>
	</form>
</section>
