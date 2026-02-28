/** Auth store using Svelte 5 runes — JWT persisted in sessionStorage to survive page reloads. */

import type { AuthTokens, User } from '$lib/types/api.js';

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
	} else {
		sessionStorage.removeItem(STORAGE_KEY);
	}
}

const initial = loadFromSession();

let accessToken = $state<string | null>(initial?.accessToken ?? null);
let refreshToken = $state<string | null>(initial?.refreshToken ?? null);
let currentUser = $state<User | null>(initial?.user ?? null);

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
	refreshToken = tokens.refresh_token;
	currentUser = user;
	saveToSession({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token, user });
}

export function updateTokens(tokens: AuthTokens): void {
	accessToken = tokens.access_token;
	refreshToken = tokens.refresh_token;
	if (currentUser) {
		saveToSession({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token, user: currentUser });
	}
}

export function clearAuth(): void {
	accessToken = null;
	refreshToken = null;
	currentUser = null;
	saveToSession(null);
}
