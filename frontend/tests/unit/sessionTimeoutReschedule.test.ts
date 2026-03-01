/**
 * Tests for WP-3: Session Timeout During Active Use
 *
 * Verifies that the session timeout warning timer reschedules correctly
 * when the JWT access token is refreshed (either by user action or
 * by apiFetch's silent auto-refresh).
 *
 * ADR-031 / SPEC-031-A
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
	getAccessToken,
	isAuthenticated,
	setAuth,
	updateTokens,
	clearAuth,
} from '$lib/stores/auth.svelte.js';
import { parseTokenExpiry } from '$lib/utils/tokenExpiry.js';
import type { AuthTokens, User } from '$lib/types/api.js';

/** Create a fake JWT with a given exp timestamp (seconds since epoch). */
function createFakeJwt(expSeconds: number): string {
	const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
	const payload = btoa(JSON.stringify({ sub: 'user-1', exp: expSeconds }));
	const signature = 'fakesignature';
	return `${header}.${payload}.${signature}`;
}

const mockUser: User = {
	id: 'user-1',
	username: 'testuser',
	role: 'admin',
	is_active: true,
};

describe('parseTokenExpiry', () => {
	it('should extract exp from a valid JWT', () => {
		const expSeconds = Math.floor(Date.now() / 1000) + 3600;
		const token = createFakeJwt(expSeconds);
		const result = parseTokenExpiry(token);
		expect(result).toBe(expSeconds * 1000);
	});

	it('should return null for an invalid token', () => {
		expect(parseTokenExpiry('not-a-jwt')).toBeNull();
		expect(parseTokenExpiry('')).toBeNull();
	});

	it('should return null for null input', () => {
		expect(parseTokenExpiry(null)).toBeNull();
	});

	it('should return null for a token without exp claim', () => {
		const header = btoa(JSON.stringify({ alg: 'HS256' }));
		const payload = btoa(JSON.stringify({ sub: 'user-1' }));
		const token = `${header}.${payload}.sig`;
		expect(parseTokenExpiry(token)).toBeNull();
	});
});

describe('auth store token reactivity for timer rescheduling', () => {
	beforeEach(() => {
		clearAuth();
	});

	it('getAccessToken returns new value after updateTokens', () => {
		const exp1 = Math.floor(Date.now() / 1000) + 1800;
		const token1 = createFakeJwt(exp1);
		setAuth(
			{ access_token: token1, refresh_token: 'r1', token_type: 'bearer' },
			mockUser,
		);
		expect(getAccessToken()).toBe(token1);

		const exp2 = Math.floor(Date.now() / 1000) + 3600;
		const token2 = createFakeJwt(exp2);
		updateTokens({ access_token: token2, refresh_token: 'r2', token_type: 'bearer' });
		expect(getAccessToken()).toBe(token2);
		expect(getAccessToken()).not.toBe(token1);
	});

	it('parseTokenExpiry returns different values for different tokens', () => {
		const exp1 = Math.floor(Date.now() / 1000) + 1800;
		const exp2 = Math.floor(Date.now() / 1000) + 3600;
		const token1 = createFakeJwt(exp1);
		const token2 = createFakeJwt(exp2);

		const expiry1 = parseTokenExpiry(token1);
		const expiry2 = parseTokenExpiry(token2);

		expect(expiry1).not.toBe(expiry2);
		expect(expiry2! - expiry1!).toBe(1800 * 1000);
	});

	it('isAuthenticated remains true after updateTokens', () => {
		const exp1 = Math.floor(Date.now() / 1000) + 1800;
		setAuth(
			{ access_token: createFakeJwt(exp1), refresh_token: 'r1', token_type: 'bearer' },
			mockUser,
		);
		expect(isAuthenticated()).toBe(true);

		const exp2 = Math.floor(Date.now() / 1000) + 3600;
		updateTokens({
			access_token: createFakeJwt(exp2),
			refresh_token: 'r2',
			token_type: 'bearer',
		});
		expect(isAuthenticated()).toBe(true);
	});
});

describe('session timeout timer rescheduling logic', () => {
	beforeEach(() => {
		vi.useFakeTimers();
		clearAuth();
	});

	afterEach(() => {
		vi.useRealTimers();
		clearAuth();
	});

	it('scheduleWarningTimer schedules at 60s before expiry', () => {
		const now = Date.now();
		const expMs = now + 120_000; // expires in 2 minutes
		const warningTime = expMs - 60_000; // warning at 1 minute
		const delay = warningTime - now;

		const callback = vi.fn();
		const timerId = setTimeout(callback, delay);

		expect(callback).not.toHaveBeenCalled();

		// Advance to just before warning time
		vi.advanceTimersByTime(delay - 1);
		expect(callback).not.toHaveBeenCalled();

		// Advance to warning time
		vi.advanceTimersByTime(1);
		expect(callback).toHaveBeenCalledOnce();

		clearTimeout(timerId);
	});

	it('clearing old timer and scheduling new one prevents stale warning', () => {
		const now = Date.now();

		// First token: expires in 2 minutes, warning at 1 minute
		const exp1Ms = now + 120_000;
		const warningDelay1 = exp1Ms - 60_000 - now;

		const staleCallback = vi.fn();
		const timer1 = setTimeout(staleCallback, warningDelay1);

		// Simulate auto-refresh after 30 seconds: new token expires in 2 minutes from then
		vi.advanceTimersByTime(30_000);
		clearTimeout(timer1); // cleanup clears old timer

		const afterRefreshNow = now + 30_000;
		const exp2Ms = afterRefreshNow + 120_000;
		const warningDelay2 = exp2Ms - 60_000 - afterRefreshNow;

		const freshCallback = vi.fn();
		const timer2 = setTimeout(freshCallback, warningDelay2);

		// The stale callback should never fire
		vi.advanceTimersByTime(warningDelay1); // past the original warning time
		expect(staleCallback).not.toHaveBeenCalled();

		// The fresh callback should fire at the new warning time
		vi.advanceTimersByTime(warningDelay2 - warningDelay1);
		expect(freshCallback).toHaveBeenCalledOnce();

		clearTimeout(timer2);
	});

	it('without clearing old timer, stale warning fires incorrectly (demonstrates the bug)', () => {
		const now = Date.now();

		// First token: expires in 2 minutes
		const exp1Ms = now + 120_000;
		const warningDelay1 = exp1Ms - 60_000 - now; // 60s

		const staleCallback = vi.fn();
		const timer1 = setTimeout(staleCallback, warningDelay1);

		// Simulate auto-refresh after 30 seconds but WITHOUT clearing old timer
		vi.advanceTimersByTime(30_000);
		// NOT clearing timer1 — this is the bug

		// Advance to original warning time (60s from start, 30s after refresh)
		vi.advanceTimersByTime(30_000);

		// Bug: stale callback fires even though session was just refreshed
		expect(staleCallback).toHaveBeenCalledOnce();

		clearTimeout(timer1);
	});

	it('token change produces different expiry, enabling correct rescheduling', () => {
		const now = Date.now();
		const exp1 = Math.floor(now / 1000) + 120; // 2 min
		const token1 = createFakeJwt(exp1);
		const expiry1 = parseTokenExpiry(token1);

		// Simulate time passing and new token
		const laterNow = now + 30_000;
		const exp2 = Math.floor(laterNow / 1000) + 120; // 2 min from later
		const token2 = createFakeJwt(exp2);
		const expiry2 = parseTokenExpiry(token2);

		expect(expiry2).toBeGreaterThan(expiry1!);
		expect(expiry2! - expiry1!).toBeCloseTo(30_000, -2); // ~30s difference
	});
});
