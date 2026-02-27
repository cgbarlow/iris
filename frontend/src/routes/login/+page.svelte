<script lang="ts">
	import { goto } from '$app/navigation';
	import { setAuth } from '$lib/stores/auth.svelte.js';
	import type { AuthTokens, User } from '$lib/types/api.js';

	let username = $state('');
	let password = $state('');
	let confirmPassword = $state('');
	let error = $state('');
	let loading = $state(false);
	let needsSetup = $state(false);
	let checkingSetup = $state(true);
	let setupComplete = $state(false);

	$effect(() => {
		checkSetupNeeded();
	});

	async function checkSetupNeeded() {
		try {
			// Try a setup call with empty body to see if setup is available
			// A 400 "Setup already completed" means users exist
			// A 422 (validation error) means setup is still needed
			const response = await fetch('/api/auth/setup', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ username: '', password: '' }),
			});
			if (response.status === 400) {
				const body = await response.json().catch(() => ({}));
				if (body.detail === 'Setup already completed') {
					needsSetup = false;
				}
			} else {
				needsSetup = true;
			}
		} catch {
			needsSetup = false;
		}
		checkingSetup = false;
	}

	async function handleSetup(event: Event) {
		event.preventDefault();
		error = '';

		if (password !== confirmPassword) {
			error = 'Passwords do not match';
			return;
		}

		loading = true;
		try {
			const response = await fetch('/api/auth/setup', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ username, password }),
			});

			if (!response.ok) {
				const body = await response.json().catch(() => ({ detail: 'Setup failed' }));
				error = body.detail || 'Setup failed';
				return;
			}

			setupComplete = true;
			needsSetup = false;
			// Clear fields for login
			password = '';
			confirmPassword = '';
		} catch {
			error = 'Unable to connect to server';
		} finally {
			loading = false;
		}
	}

	async function handleLogin(event: Event) {
		event.preventDefault();
		error = '';
		loading = true;

		try {
			const response = await fetch('/api/auth/login', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ username, password }),
			});

			if (!response.ok) {
				const body = await response.json().catch(() => ({ detail: 'Login failed' }));
				error = body.detail || 'Login failed';
				return;
			}

			const tokens: AuthTokens = await response.json();

			// Decode user from JWT payload (base64url)
			const payload = JSON.parse(atob(tokens.access_token.split('.')[1]));
			const user: User = {
				id: payload.sub,
				username: payload.username,
				role: payload.role,
				is_active: true,
			};

			setAuth(tokens, user);
			await goto('/');
		} catch (e) {
			error = 'Unable to connect to server';
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>Login — Iris</title>
</svelte:head>

<main class="flex min-h-screen items-center justify-center p-4">
	{#if checkingSetup}
		<p style="color: var(--color-muted)">Loading...</p>
	{:else if needsSetup}
		<form
			onsubmit={handleSetup}
			class="w-full max-w-sm rounded-lg p-6"
			style="background-color: var(--color-surface); border: 1px solid var(--color-border)"
			aria-label="Setup form"
		>
			<h1 class="mb-2 text-center text-2xl font-bold" style="color: var(--color-fg)">
				Welcome to Iris
			</h1>
			<p class="mb-6 text-center text-sm" style="color: var(--color-muted)">
				Create your admin account to get started.
			</p>

			{#if error}
				<div
					role="alert"
					class="mb-4 rounded p-3 text-sm"
					style="background-color: color-mix(in srgb, var(--color-danger) 15%, transparent); color: var(--color-danger)"
				>
					{error}
				</div>
			{/if}

			<div class="mb-4">
				<label for="username" class="mb-1 block text-sm font-medium" style="color: var(--color-fg)">
					Username
				</label>
				<input
					id="username"
					type="text"
					bind:value={username}
					autocomplete="username"
					required
					class="w-full rounded border px-3 py-2"
					style="background-color: var(--color-bg); border-color: var(--color-border); color: var(--color-fg)"
				/>
			</div>

			<div class="mb-4">
				<label for="password" class="mb-1 block text-sm font-medium" style="color: var(--color-fg)">
					Password
				</label>
				<input
					id="password"
					type="password"
					bind:value={password}
					autocomplete="new-password"
					required
					class="w-full rounded border px-3 py-2"
					style="background-color: var(--color-bg); border-color: var(--color-border); color: var(--color-fg)"
				/>
			</div>

			<div class="mb-6">
				<label for="confirm-password" class="mb-1 block text-sm font-medium" style="color: var(--color-fg)">
					Confirm Password
				</label>
				<input
					id="confirm-password"
					type="password"
					bind:value={confirmPassword}
					autocomplete="new-password"
					required
					class="w-full rounded border px-3 py-2"
					style="background-color: var(--color-bg); border-color: var(--color-border); color: var(--color-fg)"
				/>
			</div>

			<button
				type="submit"
				disabled={loading}
				class="w-full rounded px-4 py-2 font-medium text-white transition-colors disabled:opacity-50"
				style="background-color: var(--color-primary)"
			>
				{loading ? 'Creating account...' : 'Create Admin Account'}
			</button>
		</form>
	{:else}
		<form
			onsubmit={handleLogin}
			class="w-full max-w-sm rounded-lg p-6"
			style="background-color: var(--color-surface); border: 1px solid var(--color-border)"
			aria-label="Login form"
		>
			<h1 class="mb-6 text-center text-2xl font-bold" style="color: var(--color-fg)">
				Sign in to Iris
			</h1>

			{#if setupComplete}
				<div
					role="status"
					class="mb-4 rounded p-3 text-sm"
					style="background-color: color-mix(in srgb, var(--color-success) 15%, transparent); color: var(--color-success)"
				>
					Admin account created. Sign in to continue.
				</div>
			{/if}

			{#if error}
				<div
					role="alert"
					class="mb-4 rounded p-3 text-sm"
					style="background-color: color-mix(in srgb, var(--color-danger) 15%, transparent); color: var(--color-danger)"
				>
					{error}
				</div>
			{/if}

			<div class="mb-4">
				<label for="username" class="mb-1 block text-sm font-medium" style="color: var(--color-fg)">
					Username
				</label>
				<input
					id="username"
					type="text"
					bind:value={username}
					autocomplete="username"
					required
					class="w-full rounded border px-3 py-2"
					style="background-color: var(--color-bg); border-color: var(--color-border); color: var(--color-fg)"
					aria-describedby="username-help"
				/>
				<span id="username-help" class="sr-only">Enter your username</span>
			</div>

			<div class="mb-6">
				<label for="password" class="mb-1 block text-sm font-medium" style="color: var(--color-fg)">
					Password
				</label>
				<input
					id="password"
					type="password"
					bind:value={password}
					autocomplete="current-password"
					required
					class="w-full rounded border px-3 py-2"
					style="background-color: var(--color-bg); border-color: var(--color-border); color: var(--color-fg)"
					aria-describedby="password-help"
				/>
				<span id="password-help" class="sr-only">Enter your password</span>
			</div>

			<button
				type="submit"
				disabled={loading}
				class="w-full rounded px-4 py-2 font-medium text-white transition-colors disabled:opacity-50"
				style="background-color: var(--color-primary)"
			>
				{loading ? 'Signing in...' : 'Sign in'}
			</button>
		</form>
	{/if}
</main>
