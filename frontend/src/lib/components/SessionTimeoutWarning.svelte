<script lang="ts">
	/**
	 * Session timeout warning per WCAG 2.2.1 (Timing Adjustable).
	 * Shows a dialog 60s before JWT expiry, allowing the user to extend their session.
	 */
	import { getAccessToken, getRefreshToken, isAuthenticated } from '$lib/stores/auth.svelte.js';
	import { apiFetch } from '$lib/utils/api';

	let showWarning = $state(false);
	let secondsRemaining = $state(60);
	let intervalId: ReturnType<typeof setInterval> | undefined;
	let timeoutId: ReturnType<typeof setTimeout> | undefined;
	let dialogEl: HTMLDialogElement | undefined = $state();

	$effect(() => {
		if (!isAuthenticated()) return;

		const token = getAccessToken();
		if (!token) return;

		try {
			const payload = JSON.parse(atob(token.split('.')[1]));
			const expiresAt = payload.exp * 1000;
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
		} catch {
			// Invalid token — ignore
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
		try {
			const refresh = getRefreshToken();
			if (refresh) {
				await apiFetch('/api/auth/refresh', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ refresh_token: refresh }),
				});
			}
		} catch {
			// Refresh failed — will redirect to login on next API call
		}
		showWarning = false;
		if (intervalId) clearInterval(intervalId);
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
