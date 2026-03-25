/**
 * Auth bridge — provides Iris auth headers for Scenia API calls.
 *
 * Reads the token from the Svelte auth store first, then falls back to
 * sessionStorage (for same-tab) and localStorage (for cross-tab like /scenia).
 */

import { getAccessToken } from '$lib/stores/auth.svelte.js';

const STORAGE_KEY = 'iris_auth';

function getTokenFromStorage(): string | null {
	try {
		// Try sessionStorage first (same tab)
		const session = sessionStorage.getItem(STORAGE_KEY);
		if (session) {
			const parsed = JSON.parse(session);
			if (parsed.accessToken) return parsed.accessToken;
		}
	} catch { /* ignore */ }

	try {
		// Fall back to localStorage (cross-tab)
		const local = localStorage.getItem(STORAGE_KEY);
		if (local) {
			const parsed = JSON.parse(local);
			if (parsed.accessToken) return parsed.accessToken;
		}
	} catch { /* ignore */ }

	return null;
}

export function getAuthHeaders(): Record<string, string> {
	const token = getAccessToken() ?? getTokenFromStorage();
	if (!token) return {};
	return {
		Authorization: `Bearer ${token}`,
		'Content-Type': 'application/json',
	};
}
