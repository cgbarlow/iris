/** AI provider store — holds active providers and their availability status.
 *
 * Polled periodically from AppShell so status is always fresh by the time
 * the user reaches the Iris AI chat page.
 */

import { apiFetch } from '$lib/utils/api';
import { isAuthenticated } from '$lib/stores/auth.svelte.js';

export type ActiveProvider = {
	id: string;
	name: string;
	model: string;
	provider_type: string;
	base_url: string | null;
	is_default: boolean;
};

let providers = $state<ActiveProvider[]>([]);
let availability = $state<Record<string, boolean>>({});
let intervalId: ReturnType<typeof setInterval> | null = null;

async function fetchProviders(): Promise<void> {
	try {
		providers = await apiFetch<ActiveProvider[]>('/api/ai/providers/active');
	} catch {
		// Graceful degradation
	}
}

async function pingProviders(): Promise<void> {
	try {
		availability = await apiFetch<Record<string, boolean>>('/api/ai/providers/ping', { method: 'POST' });
	} catch {
		// ignore
	}
}

/** Start background polling. Called once from AppShell. */
export function startProviderPolling(): void {
	if (intervalId) return; // already running
	// Initial fetch
	if (isAuthenticated()) {
		fetchProviders().then(() => pingProviders());
	}
	intervalId = setInterval(() => {
		if (isAuthenticated()) pingProviders();
	}, 60000);
}

/** Stop background polling. */
export function stopProviderPolling(): void {
	if (intervalId) {
		clearInterval(intervalId);
		intervalId = null;
	}
}

/** Force a refresh of providers and availability. */
export async function refreshProviders(): Promise<void> {
	await fetchProviders();
	await pingProviders();
}

export function getActiveProviders(): ActiveProvider[] {
	return providers;
}

export function getProviderAvailability(): Record<string, boolean> {
	return availability;
}
