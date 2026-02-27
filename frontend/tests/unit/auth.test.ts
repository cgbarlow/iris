import { describe, it, expect, beforeEach } from 'vitest';
import {
	getAccessToken,
	getRefreshToken,
	getCurrentUser,
	isAuthenticated,
	setAuth,
	updateTokens,
	clearAuth,
} from '$lib/stores/auth.svelte.js';
import type { AuthTokens, User } from '$lib/types/api.js';

const mockTokens: AuthTokens = {
	access_token: 'access-123',
	refresh_token: 'refresh-456',
	token_type: 'bearer',
};

const mockUser: User = {
	id: 'user-1',
	username: 'testuser',
	role: 'admin',
	is_active: true,
};

describe('auth store', () => {
	beforeEach(() => {
		clearAuth();
	});

	it('starts unauthenticated', () => {
		expect(isAuthenticated()).toBe(false);
		expect(getAccessToken()).toBeNull();
		expect(getRefreshToken()).toBeNull();
		expect(getCurrentUser()).toBeNull();
	});

	it('setAuth stores tokens and user', () => {
		setAuth(mockTokens, mockUser);
		expect(isAuthenticated()).toBe(true);
		expect(getAccessToken()).toBe('access-123');
		expect(getRefreshToken()).toBe('refresh-456');
		expect(getCurrentUser()).toEqual(mockUser);
	});

	it('updateTokens refreshes tokens without changing user', () => {
		setAuth(mockTokens, mockUser);
		updateTokens({
			access_token: 'new-access',
			refresh_token: 'new-refresh',
			token_type: 'bearer',
		});
		expect(getAccessToken()).toBe('new-access');
		expect(getRefreshToken()).toBe('new-refresh');
		expect(getCurrentUser()).toEqual(mockUser);
	});

	it('clearAuth resets everything', () => {
		setAuth(mockTokens, mockUser);
		clearAuth();
		expect(isAuthenticated()).toBe(false);
		expect(getAccessToken()).toBeNull();
		expect(getRefreshToken()).toBeNull();
		expect(getCurrentUser()).toBeNull();
	});
});
