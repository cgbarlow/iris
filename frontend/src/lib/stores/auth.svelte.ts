/** Auth store using Svelte 5 runes.
 *
 * SQLite mode: JWT persisted in sessionStorage to survive page reloads.
 * Supabase mode: session managed by Supabase SDK; reactive via onAuthStateChange.
 */

import type { AuthTokens, User } from '$lib/types/api.js';
import { API_BASE_URL, DB_BACKEND } from '$lib/config.js';
import { supabase } from '$lib/supabase.js';

const STORAGE_KEY = 'iris_auth';

interface StoredAuth {
	accessToken: string;
	refreshToken: string;
	user: User;
}

function loadFromSession(): StoredAuth | null {
	if (typeof sessionStorage === 'undefined') return null;
	try {
		const raw = sessionStorage.getItem(STORAGE_KEY);
		if (!raw) return null;
		return JSON.parse(raw) as StoredAuth;
	} catch {
		return null;
	}
}

function saveToSession(data: StoredAuth | null): void {
	if (typeof sessionStorage === 'undefined') return;
	if (data) {
		sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
		localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
	} else {
		sessionStorage.removeItem(STORAGE_KEY);
		localStorage.removeItem(STORAGE_KEY);
	}
}

const initial = loadFromSession();

let accessToken = $state<string | null>(initial?.accessToken ?? null);
let refreshToken = $state<string | null>(initial?.refreshToken ?? null);
let currentUser = $state<User | null>(initial?.user ?? null);

// Supabase mode: keep access token in sync with the Supabase session.
// onAuthStateChange fires on SIGNED_IN, TOKEN_REFRESHED, and SIGNED_OUT.
async function _fetchProfile(token: string): Promise<void> {
	try {
		const resp = await fetch(`${API_BASE_URL}/api/auth/me`, {
			headers: { Authorization: `Bearer ${token}` },
		});
		if (resp.ok) {
			currentUser = await resp.json();
		}
	} catch {
		// Profile fetch failed — user will see partial auth state
	}
}

if (DB_BACKEND === 'supabase' && supabase) {
	supabase.auth.getSession().then(({ data: { session } }) => {
		if (session) {
			accessToken = session.access_token;
			refreshToken = session.refresh_token;
			saveToSession({ accessToken: session.access_token, refreshToken: session.refresh_token, user: currentUser! });
			if (!currentUser) {
				_fetchProfile(session.access_token);
			}
		}
	});

	supabase.auth.onAuthStateChange((_event, session) => {
		if (session) {
			accessToken = session.access_token;
			refreshToken = session.refresh_token;
			// Persist to storage so cross-window consumers (e.g. Scenia) can read the token
			saveToSession({ accessToken: session.access_token, refreshToken: session.refresh_token, user: currentUser! });
			if (!currentUser) {
				_fetchProfile(session.access_token);
			}
		} else {
			accessToken = null;
			refreshToken = null;
			currentUser = null;
			saveToSession(null);
		}
	});
}

export function getAccessToken(): string | null {
	return accessToken;
}

export function getRefreshToken(): string | null {
	return refreshToken;
}

export function getCurrentUser(): User | null {
	return currentUser;
}

export function isAuthenticated(): boolean {
	return accessToken !== null;
}

export function setAuth(tokens: AuthTokens, user: User): void {
	accessToken = tokens.access_token;
	refreshToken = tokens.refresh_token ?? null;
	currentUser = user;
	if (DB_BACKEND !== 'supabase') {
		saveToSession({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token, user });
	}
}

export function updateTokens(tokens: AuthTokens): void {
	accessToken = tokens.access_token;
	refreshToken = tokens.refresh_token ?? null;
	if (DB_BACKEND !== 'supabase' && currentUser) {
		saveToSession({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token, user: currentUser });
	}
}

export function clearAuth(): void {
	accessToken = null;
	refreshToken = null;
	currentUser = null;
	if (DB_BACKEND === 'supabase' && supabase) {
		// Fire-and-forget: state is already cleared above; signOut revokes the server session.
		supabase.auth.signOut().catch(() => undefined);
	} else {
		saveToSession(null);
	}
}
