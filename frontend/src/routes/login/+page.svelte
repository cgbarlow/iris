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

	type View = 'login' | 'setup' | 'request-account' | 'forgot-password';
	let view = $state<View>('login');

	$effect(() => {
		checkSetupNeeded();
	});

	async function checkSetupNeeded() {
		try {
			const response = await fetch('/api/auth/setup/status');
			if (response.ok) {
				const data = await response.json();
				needsSetup = data.needs_setup === true;
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

	{:else if needsSetup || view === 'setup'}
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
				<label for="setup-username" class="mb-1 block text-sm font-medium" style="color: var(--color-fg)">
					Username
				</label>
				<input
					id="setup-username"
					type="text"
					bind:value={username}
					autocomplete="username"
					required
					class="w-full rounded border px-3 py-2"
					style="background-color: var(--color-bg); border-color: var(--color-border); color: var(--color-fg)"
				/>
			</div>

			<div class="mb-4">
				<label for="setup-password" class="mb-1 block text-sm font-medium" style="color: var(--color-fg)">
					Password
				</label>
				<input
					id="setup-password"
					type="password"
					bind:value={password}
					autocomplete="new-password"
					required
					class="w-full rounded border px-3 py-2"
					style="background-color: var(--color-bg); border-color: var(--color-border); color: var(--color-fg)"
				/>
			</div>

			<div class="mb-6">
				<label for="setup-confirm-password" class="mb-1 block text-sm font-medium" style="color: var(--color-fg)">
					Confirm Password
				</label>
				<input
					id="setup-confirm-password"
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

	{:else if view === 'request-account'}
		<div
			class="w-full max-w-sm rounded-lg p-6"
			style="background-color: var(--color-surface); border: 1px solid var(--color-border)"
		>
			<h1 class="mb-2 text-center text-2xl font-bold" style="color: var(--color-fg)">
				Request an Account
			</h1>
			<p class="mb-4 text-center text-sm" style="color: var(--color-muted)">
				Iris uses managed accounts. To get access, please contact your system administrator and request a new user account.
			</p>
			<div
				class="mb-6 rounded p-4 text-sm"
				style="background-color: color-mix(in srgb, var(--color-primary) 10%, transparent); color: var(--color-fg)"
			>
				<p class="font-medium">Your administrator can:</p>
				<ul class="mt-2 list-inside list-disc" style="color: var(--color-muted)">
					<li>Create your account from the Admin panel</li>
					<li>Assign your role (Viewer, Reviewer, Architect, or Admin)</li>
					<li>Provide you with login credentials</li>
				</ul>
			</div>
			<button
				onclick={() => { error = ''; view = 'login'; }}
				class="w-full rounded px-4 py-2 font-medium transition-colors"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				Back to Sign In
			</button>
		</div>

	{:else if view === 'forgot-password'}
		<div
			class="w-full max-w-sm rounded-lg p-6"
			style="background-color: var(--color-surface); border: 1px solid var(--color-border)"
		>
			<h1 class="mb-2 text-center text-2xl font-bold" style="color: var(--color-fg)">
				Forgot Password
			</h1>
			<p class="mb-4 text-center text-sm" style="color: var(--color-muted)">
				Password resets are handled by your system administrator.
			</p>
			<div
				class="mb-6 rounded p-4 text-sm"
				style="background-color: color-mix(in srgb, var(--color-primary) 10%, transparent); color: var(--color-fg)"
			>
				<p class="font-medium">To reset your password:</p>
				<ul class="mt-2 list-inside list-disc" style="color: var(--color-muted)">
					<li>Contact your system administrator</li>
					<li>They can reset your password from the Admin panel</li>
					<li>You will be given temporary credentials to sign in</li>
				</ul>
			</div>
			<button
				onclick={() => { error = ''; view = 'login'; }}
				class="w-full rounded px-4 py-2 font-medium transition-colors"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				Back to Sign In
			</button>
		</div>

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

			<div class="mb-4">
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

			<div class="mt-4 flex justify-between text-sm">
				<button
					type="button"
					onclick={() => { error = ''; view = 'request-account'; }}
					class="underline"
					style="color: var(--color-primary)"
				>
					Request an account
				</button>
				<button
					type="button"
					onclick={() => { error = ''; view = 'forgot-password'; }}
					class="underline"
					style="color: var(--color-primary)"
				>
					Forgot password?
				</button>
			</div>
		</form>
	{/if}
</main>
