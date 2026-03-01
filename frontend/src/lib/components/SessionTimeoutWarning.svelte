<script lang="ts">
	/**
	 * Session timeout warning per WCAG 2.2.1 (Timing Adjustable).
	 * Shows a dialog 60s before JWT expiry, allowing the user to extend their session.
	 *
	 * ADR-031: The $effect reads getAccessToken() FIRST (before any early returns)
	 * to ensure Svelte 5 tracks the $state dependency. This guarantees the effect
	 * re-runs whenever the token changes — including silent auto-refresh by apiFetch.
	 */
	import { getAccessToken, isAuthenticated, clearAuth } from '$lib/stores/auth.svelte.js';
	import { tryRefresh } from '$lib/utils/api';
	import { parseTokenExpiry } from '$lib/utils/tokenExpiry.js';

	let showWarning = $state(false);
	let secondsRemaining = $state(60);
	let intervalId: ReturnType<typeof setInterval> | undefined;
	let timeoutId: ReturnType<typeof setTimeout> | undefined;
	let dialogEl: HTMLDialogElement | undefined = $state();

	$effect(() => {
		// ADR-031: Read token FIRST to ensure Svelte tracks the $state dependency.
		// This must happen before any early returns so the effect re-runs whenever
		// updateTokens() or setAuth() writes a new token value (e.g. auto-refresh).
		const token = getAccessToken();

		if (!isAuthenticated()) return;
		if (!token) return;

		const expiresAt = parseTokenExpiry(token);
		if (!expiresAt) return;

		const warningTime = expiresAt - 60_000;
		const now = Date.now();

		if (warningTime > now) {
			timeoutId = setTimeout(() => {
				showWarning = true;
				secondsRemaining = 60;
				intervalId = setInterval(() => {
					secondsRemaining--;
					if (secondsRemaining <= 0) {
						clearInterval(intervalId);
					}
				}, 1000);
			}, warningTime - now);
		}

		return () => {
			if (timeoutId) clearTimeout(timeoutId);
			if (intervalId) clearInterval(intervalId);
		};
	});

	$effect(() => {
		if (showWarning && dialogEl && !dialogEl.open) {
			dialogEl.showModal();
		} else if (!showWarning && dialogEl?.open) {
			dialogEl.close();
		}
	});

	async function extendSession() {
		const success = await tryRefresh();
		if (success) {
			// Re-schedule warning timer with new token's expiry
			if (timeoutId) clearTimeout(timeoutId);
			if (intervalId) clearInterval(intervalId);
			showWarning = false;
			// The $effect watching isAuthenticated/getAccessToken will re-schedule
		} else {
			clearAuth();
			showWarning = false;
			if (intervalId) clearInterval(intervalId);
		}
	}

	function dismiss() {
		showWarning = false;
		if (intervalId) clearInterval(intervalId);
	}
</script>

{#if showWarning}
	<dialog
		bind:this={dialogEl}
		aria-labelledby="session-timeout-title"
		aria-describedby="session-timeout-message"
		class="rounded-lg p-6 shadow-lg backdrop:bg-black/50"
		style="background-color: var(--color-surface); color: var(--color-fg); border: 1px solid var(--color-border)"
	>
		<h2 id="session-timeout-title" class="text-lg font-bold">Session Expiring</h2>
		<p id="session-timeout-message" class="mt-2" style="color: var(--color-muted)">
			Your session will expire in {secondsRemaining} seconds. Would you like to continue?
		</p>

		<div class="mt-6 flex justify-end gap-3">
			<button
				onclick={dismiss}
				class="rounded px-4 py-2 text-sm"
				style="border: 1px solid var(--color-border); color: var(--color-fg)"
			>
				Sign out
			</button>
			<button
				onclick={extendSession}
				class="rounded px-4 py-2 text-sm text-white"
				style="background-color: var(--color-primary)"
			>
				Continue session
			</button>
		</div>
	</dialog>
{/if}
