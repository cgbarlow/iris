<script lang="ts">
	import { goto } from '$app/navigation';
	import { setAuth } from '$lib/stores/auth.svelte.js';
	import type { AuthTokens, User } from '$lib/types/api.js';

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);

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
	<form
		onsubmit={handleLogin}
		class="w-full max-w-sm rounded-lg p-6"
		style="background-color: var(--color-surface); border: 1px solid var(--color-border)"
		aria-label="Login form"
	>
		<h1 class="mb-6 text-center text-2xl font-bold" style="color: var(--color-fg)">
			Sign in to Iris
		</h1>

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
</main>
