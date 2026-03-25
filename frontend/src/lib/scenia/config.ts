/**
 * Scenia standalone app URL and link builder.
 */

/** Base URL of the Scenia dev server. */
export const SCENIA_URL: string = import.meta.env.VITE_SCENIA_URL ?? 'http://localhost:3000';

/** Backend API URL for Scenia to call directly (not via Vite proxy). */
const IRIS_API_URL: string = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const STORAGE_KEY = 'iris_auth';

/** Get the auth token, reading from storage if the store hasn't hydrated. */
function getToken(): string {
	// Try sessionStorage first, then localStorage
	for (const storage of [sessionStorage, localStorage]) {
		try {
			const raw = storage.getItem(STORAGE_KEY);
			if (raw) {
				const parsed = JSON.parse(raw);
				if (parsed.accessToken) return parsed.accessToken;
			}
		} catch { /* ignore */ }
	}
	return '';
}

/** Open Scenia in a new window with Iris API connection params. */
export function openScenia(setId: string, focusId?: string): void {
	const token = getToken();
	if (!token) {
		alert('Not authenticated. Please log in first.');
		return;
	}
	const url = new URL(SCENIA_URL);
	url.searchParams.set('apiUrl', IRIS_API_URL);
	url.searchParams.set('token', token);
	url.searchParams.set('setId', setId);
	if (focusId) url.searchParams.set('focus', focusId);
	window.open(url.toString(), '_blank');
}
