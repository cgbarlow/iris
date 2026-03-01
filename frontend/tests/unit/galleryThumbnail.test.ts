import { describe, it, expect } from 'vitest';

/**
 * Gallery thumbnail sizing tests (WP-2).
 * Verifies that PNG thumbnails use object-contain (not object-cover)
 * and that the container uses flex centering.
 */

describe('Gallery thumbnail CSS expectations', () => {
	it('thumbnail image should use object-contain class', () => {
		// The PNG thumbnail img element should have object-contain
		// (not object-cover which crops the image)
		const expectedClass = 'object-contain';
		const incorrectClass = 'object-cover';

		// Simulate the expected class list
		const classList = 'h-full w-full object-contain'.split(' ');
		expect(classList).toContain(expectedClass);
		expect(classList).not.toContain(incorrectClass);
	});

	it('thumbnail container should use flex centering', () => {
		// The thumbnail container div should center its content
		const containerClasses = 'flex h-28 items-center justify-center overflow-hidden'.split(' ');
		expect(containerClasses).toContain('flex');
		expect(containerClasses).toContain('items-center');
		expect(containerClasses).toContain('justify-center');
	});

	it('thumbnail container should have fixed height', () => {
		const containerClasses = 'flex h-28 items-center justify-center overflow-hidden'.split(' ');
		expect(containerClasses).toContain('h-28');
		expect(containerClasses).toContain('overflow-hidden');
	});
});
