import { describe, it, expect } from 'vitest';
import { ApiError } from '$lib/utils/api.js';

describe('ApiError', () => {
	it('should have correct status and message', () => {
		const error = new ApiError(404, 'Not Found');
		expect(error.status).toBe(404);
		expect(error.message).toBe('Not Found');
		expect(error.name).toBe('ApiError');
	});

	it('should be an instance of Error', () => {
		const error = new ApiError(500, 'Server Error');
		expect(error).toBeInstanceOf(Error);
	});
});
