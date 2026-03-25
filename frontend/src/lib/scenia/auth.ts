/**
 * Auth bridge — provides Iris auth headers for Scenia API calls.
 */

import { getAccessToken } from '$lib/stores/auth.svelte.js';

export function getAuthHeaders(): Record<string, string> {
	const token = getAccessToken();
	if (!token) return {};
	return {
		Authorization: `Bearer ${token}`,
		'Content-Type': 'application/json',
	};
}
