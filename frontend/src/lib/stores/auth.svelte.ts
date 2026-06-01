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
		// v5.17.0 (ADR-162): sessionStorage is per-tab. Fall back to
		// localStorage if a sibling tab already saved auth there, then
		// re-seed sessionStorage so this tab caches it going forward.
		// Fixes "new tab opened from Claude's pairing link sees user as
		// anonymous" symptom.
		let raw = sessionStorage.getItem(STORAGE_KEY);
		if (!raw && typeof localStorage !== 'undefined') {
			raw = localStorage.getItem(STORAGE_KEY);
			if (raw) sessionStorage.setItem(STORAGE_KEY, raw);
		}
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

/** True when no access token is present — the caller is browsing anonymously.
 *  Used by components to hide write UI (ADR-123). */
export function isAnonymous(): boolean {
	return accessToken === null;
}

/** ADR-237: the user is restricted to a whitelist of writable collections.
 *  `write_scope` is a string[] when scoped, null when unrestricted (admins or
 *  users with no scope rows), and may be undefined before the profile loads. */
export function isScoped(): boolean {
	return Array.isArray(currentUser?.write_scope);
}

/** ADR-237: may the current user WRITE in this collection? Unrestricted users
 *  always can; scoped users only within their whitelist. A null/unknown
 *  collection id is not writable for scoped users. The backend enforces this
 *  regardless — this only gates UI affordances so they match permissions. */
export function canWrite(collectionId: string | null | undefined): boolean {
	const scope = currentUser?.write_scope;
	if (!Array.isArray(scope)) return true; // unrestricted (or profile not yet loaded)
	return collectionId != null && scope.includes(collectionId);
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
