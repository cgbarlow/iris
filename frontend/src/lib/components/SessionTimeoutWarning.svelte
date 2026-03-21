<script lang="ts">
	/**
	 * Session timeout warning per WCAG 2.2.1 (Timing Adjustable).
	 *
	 * If the user is active (mouse/keyboard/touch in the last 2 minutes),
	 * silently auto-refreshes the token before the warning would appear.
	 * Only shows the dialog if the user has been truly idle.
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

	// Track user activity — any interaction resets the timestamp
	let lastActivity = Date.now();
	const IDLE_THRESHOLD = 2 * 60 * 1000; // 2 minutes

	function onUserActivity() {
		lastActivity = Date.now();
	}

	$effect(() => {
		const events = ['mousedown', 'mousemove', 'keydown', 'scroll', 'touchstart', 'click'] as const;
		for (const e of events) window.addEventListener(e, onUserActivity, { passive: true });
		return () => {
			for (const e of events) window.removeEventListener(e, onUserActivity);
		};
	});

	$effect(() => {
		// ADR-031: Read token FIRST to ensure Svelte tracks the $state dependency.
		const token = getAccessToken();

		if (!isAuthenticated()) return;
		if (!token) return;

		const expiresAt = parseTokenExpiry(token);
		if (!expiresAt) return;

		// Schedule check 90s before expiry — enough time to auto-refresh silently
		const checkTime = expiresAt - 90_000;
		const now = Date.now();

		if (checkTime > now) {
			timeoutId = setTimeout(async () => {
				const isActive = (Date.now() - lastActivity) < IDLE_THRESHOLD;

				if (isActive) {
					// User is active — silently refresh, no dialog needed
					const success = await tryRefresh();
					if (!success) {
						clearAuth();
					}
					// $effect will re-run with the new token and re-schedule
				} else {
					// User is idle — show the warning dialog
					showWarning = true;
					secondsRemaining = Math.round((expiresAt - Date.now()) / 1000);
					intervalId = setInterval(() => {
						secondsRemaining--;
						if (secondsRemaining <= 0) {
							clearInterval(intervalId);
						}
					}, 1000);
				}
			}, checkTime - now);
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
			if (timeoutId) clearTimeout(timeoutId);
			if (intervalId) clearInterval(intervalId);
			showWarning = false;
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
