import { describe, it, expect } from 'vitest';
import { tryRefresh, ApiError } from '$lib/utils/api.js';

describe('tryRefresh export', () => {
	it('should be exported as a function', () => {
		expect(tryRefresh).toBeDefined();
		expect(typeof tryRefresh).toBe('function');
	});

	it('should return a Promise when called', () => {
		// tryRefresh() will attempt a fetch and fail in test environment,
		// but it should still return a Promise<boolean>
		const result = tryRefresh();
		expect(result).toBeInstanceOf(Promise);
		// Let it resolve (will return false due to no refresh token in store)
		return result.then((value) => {
			expect(typeof value).toBe('boolean');
		});
	});

	it('should return false when no refresh token is available', async () => {
		// With no auth state set, getRefreshToken() returns null
		const result = await tryRefresh();
		expect(result).toBe(false);
	});
});

describe('ApiError (regression guard)', () => {
	it('should still be exported alongside tryRefresh', () => {
		expect(ApiError).toBeDefined();
		const error = new ApiError(401, 'Unauthorized');
		expect(error.status).toBe(401);
		expect(error.message).toBe('Unauthorized');
	});
});
