/** Auth store using Svelte 5 runes — in-memory JWT only (no localStorage). */

import type { AuthTokens, User } from '$lib/types/api.js';

let accessToken = $state<string | null>(null);
let currentUser = $state<User | null>(null);

export function getAccessToken(): string | null {
	return accessToken;
}

export function getCurrentUser(): User | null {
	return currentUser;
}

export function isAuthenticated(): boolean {
	return accessToken !== null;
}

export function setAuth(tokens: AuthTokens, user: User): void {
	accessToken = tokens.access_token;
	currentUser = user;
}

export function clearAuth(): void {
	accessToken = null;
	currentUser = null;
}
