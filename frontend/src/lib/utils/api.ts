/** API fetch wrapper with auth token injection and auto-refresh. */

import { getAccessToken, clearAuth } from '$lib/stores/auth.svelte.js';

const BASE_URL = '';

export class ApiError extends Error {
	constructor(
		public status: number,
		message: string,
	) {
		super(message);
		this.name = 'ApiError';
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

	const response = await fetch(`${BASE_URL}${path}`, {
		...options,
		headers,
	});

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
