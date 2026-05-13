<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import DOMPurify from 'dompurify';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import { isAuthenticated } from '$lib/stores/auth.svelte.js';

	type ConsentPayload = {
		request_id: string;
		client_id: string;
		client_name: string;
		user_id: string;
		username: string;
		redirect_uri: string;
		state: string | null;
		scope: string;
		code_challenge: string;
		code_challenge_method: string;
	};

	let consent = $state<ConsentPayload | null>(null);
	let error = $state('');
	let busy = $state(false);

	// v6.0.0 (ADR-164): if the user isn't signed in, bounce them
	// through /login with redirect-back to this very page.
	onMount(async () => {
		if (!isAuthenticated()) {
			const here = window.location.pathname + window.location.search;
			await goto(`/login?redirect=${encodeURIComponent(here)}`);
			return;
		}
		try {
			const body = {
				response_type: page.url.searchParams.get('response_type'),
				client_id: page.url.searchParams.get('client_id'),
				redirect_uri: page.url.searchParams.get('redirect_uri'),
				code_challenge: page.url.searchParams.get('code_challenge'),
				code_challenge_method: page.url.searchParams.get('code_challenge_method'),
				scope: page.url.searchParams.get('scope') ?? 'iris',
				state: page.url.searchParams.get('state'),
			};
			consent = await apiFetch('/api/oauth/authorize/prepare', {
				method: 'POST',
				body: JSON.stringify(body),
			}) as ConsentPayload;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Failed to load consent screen.';
		}
	});

	async function decide(allow: boolean) {
		if (!consent || busy) return;
		busy = true;
		try {
			const result = await apiFetch('/api/oauth/authorize/decision', {
				method: 'POST',
				body: JSON.stringify({
					request_id: consent.request_id,
					decision: allow ? 'allow' : 'deny',
				}),
			}) as { redirect_to: string };
			window.location.href = result.redirect_to;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Decision failed.';
			busy = false;
		}
	}

	// DCR-supplied content is untrusted — sanitise per protocol §7.
	const safeClientName = $derived(consent ? DOMPurify.sanitize(consent.client_name) : '');
</script>

<svelte:head>
	<title>Authorize MCP client — Iris</title>
</svelte:head>

<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Authorize MCP client</h1>

{#if error}
	<section class="mt-6 rounded border px-4 py-3 text-sm"
		style="border-color: var(--color-error); color: var(--color-error); background-color: var(--color-bg)">
		{error}
	</section>
{:else if !consent}
	<p class="mt-6 text-sm" style="color: var(--color-muted)">Loading…</p>
{:else}
	<p class="mt-4 text-base" style="color: var(--color-fg)">
		<strong>{@html safeClientName}</strong> wants to access Iris on your behalf as
		<strong>{consent.username}</strong>.
	</p>

	<p class="mt-3 text-sm" style="color: var(--color-muted)">
		This grants the scope <code class="font-mono">{consent.scope}</code> (full access to your Iris
		data). You can revoke this access from /admin in the future.
	</p>

	<div class="mt-6 flex gap-3">
		<button
			type="button"
			onclick={() => decide(true)}
			disabled={busy}
			data-testid="oauth-allow"
			class="rounded px-4 py-2 text-sm text-white"
			style="background-color: var(--color-primary); opacity: {busy ? '0.6' : '1'}; cursor: {busy ? 'not-allowed' : 'pointer'}"
		>
			{busy ? 'Working…' : 'Allow'}
		</button>
		<button
			type="button"
			onclick={() => decide(false)}
			disabled={busy}
			data-testid="oauth-deny"
			class="rounded border px-4 py-2 text-sm"
			style="border-color: var(--color-border); color: var(--color-fg); background-color: var(--color-bg); opacity: {busy ? '0.6' : '1'}; cursor: {busy ? 'not-allowed' : 'pointer'}"
		>
			Deny
		</button>
	</div>
{/if}
