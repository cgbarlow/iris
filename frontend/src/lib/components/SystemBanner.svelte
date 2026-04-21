<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { apiFetch } from '$lib/utils/api';

	// Admin-posted system banner shown to every visitor (ADR-124 /
	// SPEC-124-A). Polls the public endpoint every 60 s. Dismissal is
	// per-browser-session, per-message (hash-keyed) so a new message
	// from the admin re-appears after a previous dismiss.
	const POLL_MS = 60_000;
	const STORAGE_PREFIX = 'iris-banner-dismissed:';

	let message = $state('');
	let dismissed = $state(false);
	let pollTimer: ReturnType<typeof setInterval> | undefined;

	function hashMsg(s: string): string {
		let h = 0;
		for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0;
		return Math.abs(h).toString(36);
	}

	async function load() {
		try {
			const data = await apiFetch<{ message: string }>('/api/notifications/banner');
			message = data.message ?? '';
			dismissed = message
				? localStorage.getItem(STORAGE_PREFIX + hashMsg(message)) === '1'
				: false;
		} catch {
			// Banner is non-critical — silent failure keeps the rest of
			// the UI responsive if the endpoint is unreachable.
		}
	}

	function dismiss() {
		if (!message) return;
		localStorage.setItem(STORAGE_PREFIX + hashMsg(message), '1');
		dismissed = true;
	}

	onMount(() => {
		load();
		pollTimer = setInterval(load, POLL_MS);
	});
	onDestroy(() => clearInterval(pollTimer));
</script>

{#if message && !dismissed}
	<div class="system-banner" role="status" aria-live="polite" data-testid="system-banner">
		<span class="system-banner-text">{message}</span>
		<button
			class="system-banner-dismiss"
			aria-label="Dismiss notification"
			onclick={dismiss}
		>×</button>
	</div>
{/if}

<style>
	.system-banner {
		position: sticky;
		top: 0;
		z-index: 40;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		padding: 0.5rem 1rem;
		background: var(--color-warning, #fef3c7);
		color: var(--color-warning-fg, #78350f);
		border-bottom: 1px solid var(--color-border, #d6a93a);
		font-size: 0.875rem;
		line-height: 1.3;
	}
	.system-banner-text {
		flex: 1 1 auto;
		white-space: pre-line;
	}
	.system-banner-dismiss {
		flex: 0 0 auto;
		background: transparent;
		border: none;
		color: inherit;
		cursor: pointer;
		font-size: 1.25rem;
		line-height: 1;
		padding: 0 0.25rem;
	}
	.system-banner-dismiss:hover {
		opacity: 0.7;
	}
</style>
