<script lang="ts">
	import { onDestroy } from 'svelte';
	import { apiFetch, ApiError } from '$lib/utils/api';
	import { isAuthenticated } from '$lib/stores/auth.svelte.js';

	type PairingCode = {
		code: string;
		expires_at: string;
	};

	let pairing = $state<PairingCode | null>(null);
	let loading = $state(false);
	let error = $state('');
	let copied = $state(false);
	let secondsRemaining = $state(0);

	let countdownTimer: ReturnType<typeof setInterval> | null = null;

	function clearCountdown() {
		if (countdownTimer) {
			clearInterval(countdownTimer);
			countdownTimer = null;
		}
	}

	function startCountdown(expiresAt: string) {
		clearCountdown();
		const expiresMs = new Date(expiresAt).getTime();
		const tick = () => {
			secondsRemaining = Math.max(0, Math.round((expiresMs - Date.now()) / 1000));
			if (secondsRemaining === 0) {
				pairing = null;
				clearCountdown();
			}
		};
		tick();
		countdownTimer = setInterval(tick, 1000);
	}

	function formatRemaining(s: number): string {
		const mm = Math.floor(s / 60).toString().padStart(2, '0');
		const ss = (s % 60).toString().padStart(2, '0');
		return `${mm}:${ss}`;
	}

	async function generateCode() {
		error = '';
		copied = false;
		loading = true;
		try {
			const data = await apiFetch('/api/auth/pairing-codes', {
				method: 'POST',
				body: JSON.stringify({}),
			}) as PairingCode;
			pairing = data;
			startCountdown(data.expires_at);
		} catch (err) {
			pairing = null;
			error = err instanceof ApiError ? err.message : 'Failed to generate code.';
		} finally {
			loading = false;
		}
	}

	async function copyCode() {
		if (!pairing) return;
		try {
			await navigator.clipboard.writeText(pairing.code);
			copied = true;
			setTimeout(() => {
				copied = false;
			}, 2000);
		} catch {
			/* clipboard may not be available; user can copy manually */
		}
	}

	onDestroy(clearCountdown);
</script>

<svelte:head>
	<title>MCP Pairing — Iris</title>
</svelte:head>

<h1 class="text-2xl font-bold" style="color: var(--color-fg)">Connect an MCP client</h1>
<p class="mt-1 text-sm" style="color: var(--color-muted)">
	MCP clients (Claude Desktop, Claude Code, etc.) can authenticate to Iris by
	exchanging a one-time pairing code. This avoids editing your client's config
	file with a long-lived token.
</p>

{#if !isAuthenticated()}
	<section class="mt-6 rounded border px-4 py-3 text-sm"
		style="border-color: var(--color-border); color: var(--color-muted); background-color: var(--color-bg)">
		Sign in first to generate a pairing code.
	</section>
{:else}
	<section class="mt-6">
		<button
			type="button"
			onclick={generateCode}
			disabled={loading}
			class="rounded px-4 py-2 text-sm text-white"
			style="background-color: var(--color-primary); opacity: {loading ? '0.6' : '1'}; cursor: {loading ? 'not-allowed' : 'pointer'}"
		>
			{loading ? 'Generating…' : 'Generate pairing code'}
		</button>

		{#if error}
			<p role="alert" class="mt-4 rounded border px-4 py-2 text-sm"
				style="color: var(--color-error); border-color: var(--color-error); background-color: var(--color-bg)">
				{error}
			</p>
		{/if}

		{#if pairing}
			<div class="mt-6 rounded border px-4 py-4"
				style="border-color: var(--color-border); background-color: var(--color-bg)">
				<p class="text-sm" style="color: var(--color-muted)">Your pairing code</p>
				<div class="mt-2 flex items-center gap-3">
					<code class="text-2xl font-mono tracking-wide" style="color: var(--color-fg)"
						data-testid="pairing-code">{pairing.code}</code>
					<button
						type="button"
						onclick={copyCode}
						class="rounded border px-3 py-1 text-xs"
						style="border-color: var(--color-border); color: var(--color-fg); background-color: var(--color-bg)"
					>
						{copied ? 'Copied' : 'Copy'}
					</button>
				</div>
				<p class="mt-2 text-xs" style="color: var(--color-muted)" data-testid="pairing-countdown">
					Expires in {formatRemaining(secondsRemaining)}.
				</p>
			</div>

			<ol class="mt-6 list-decimal pl-5 text-sm" style="color: var(--color-fg)">
				<li>Copy the code above.</li>
				<li>
					In your MCP client, paste the code when prompted, or say
					<code class="font-mono" style="color: var(--color-fg)">iris_authenticate('{pairing.code}')</code>.
				</li>
				<li>
					The MCP server will exchange the code for a token and persist it
					to <code class="font-mono">~/.iris-mcp/&lt;hash&gt;.json</code> (mode 0600).
					One-time setup per machine.
				</li>
			</ol>
		{/if}
	</section>

	<section class="mt-8 rounded border px-4 py-3 text-xs"
		style="border-color: var(--color-border); color: var(--color-muted); background-color: var(--color-bg)">
		<p class="font-semibold" style="color: var(--color-fg)">Power user: paste a PAT directly</p>
		<p class="mt-1">
			If you already have a Personal Access Token, you can call
			<code class="font-mono">iris_authenticate('iris_pat_…')</code> instead of
			generating a pairing code. The MCP server will validate the token, persist
			it locally, and apply it to subsequent calls.
		</p>
	</section>
{/if}
