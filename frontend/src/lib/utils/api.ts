/** API fetch wrapper with auth token injection and auto-refresh. */

import {
	getAccessToken,
	getRefreshToken,
	updateTokens,
	clearAuth,
} from '$lib/stores/auth.svelte.js';
import { API_BASE_URL, DB_BACKEND } from '$lib/config.js';
import { supabase } from '$lib/supabase.js';
import type { AuthTokens } from '$lib/types/api.js';

export class ApiError extends Error {
	constructor(
		public status: number,
		message: string,
	) {
		super(message);
		this.name = 'ApiError';
	}
}

let refreshPromise: Promise<boolean> | null = null;

export async function tryRefresh(): Promise<boolean> {
	// Supabase mode: delegate token refresh to the Supabase SDK.
	if (DB_BACKEND === 'supabase' && supabase) {
		try {
			const { data, error } = await supabase.auth.refreshSession();
			if (error || !data.session) {
				clearAuth();
				return false;
			}
			// onAuthStateChange will update the store; updateTokens keeps it in sync now.
			updateTokens({ access_token: data.session.access_token, refresh_token: data.session.refresh_token });
			return true;
		} catch {
			clearAuth();
			return false;
		}
	}

	// SQLite mode: use the Iris /api/auth/refresh endpoint.
	const token = getRefreshToken();
	if (!token) return false;

	try {
		const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ refresh_token: token }),
		});

		if (!response.ok) {
			clearAuth();
			return false;
		}

		const tokens: AuthTokens = await response.json();
		updateTokens(tokens);
		return true;
	} catch {
		clearAuth();
		return false;
	}
}

export async function apiFetch<T>(
	path: string,
	options: RequestInit = {},
): Promise<T> {
	const token = getAccessToken();
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...(options.headers as Record<string, string>),
	};

	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}

	let response = await fetch(`${API_BASE_URL}${path}`, {
		...options,
		headers,
	});

	// Auto-refresh on 401 (Supabase SDK manages its own refresh tokens internally)
	if (response.status === 401 && (getRefreshToken() || DB_BACKEND === 'supabase')) {
		// Deduplicate concurrent refresh attempts
		if (!refreshPromise) {
			refreshPromise = tryRefresh().finally(() => {
				refreshPromise = null;
			});
		}

		const refreshed = await refreshPromise;
		if (refreshed) {
			const newToken = getAccessToken();
			if (newToken) {
				headers['Authorization'] = `Bearer ${newToken}`;
			}
			response = await fetch(`${API_BASE_URL}${path}`, {
				...options,
				headers,
			});
		}
	}

	if (response.status === 401) {
		clearAuth();
		throw new ApiError(401, 'Unauthorized');
	}

	if (!response.ok) {
		const body = await response.json().catch(() => ({ detail: response.statusText }));
		throw new ApiError(response.status, body.detail || response.statusText);
	}

	if (response.status === 204) {
		return undefined as T;
	}

	return response.json();
}
