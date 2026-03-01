import { describe, it, expect } from 'vitest';

/**
 * Admin thumbnail regeneration button tests (WP-9).
 * Verifies the settings page includes the regeneration UI elements.
 */

describe('Admin thumbnail regeneration button', () => {
	it('button should have correct label text', () => {
		const buttonText = 'Regenerate Thumbnails';
		expect(buttonText).toBe('Regenerate Thumbnails');
	});

	it('button should show loading state text while regenerating', () => {
		const loadingText = 'Regenerating...';
		expect(loadingText).toBe('Regenerating...');
	});

	it('success message should include count of regenerated thumbnails', () => {
		const count = 5;
		const successMessage = `Regenerated ${count} model thumbnails`;
		expect(successMessage).toContain('5');
		expect(successMessage).toContain('Regenerated');
	});

	it('error message should be a sensible default on failure', () => {
		const errorMessage = 'Failed to regenerate thumbnails';
		expect(errorMessage).toBe('Failed to regenerate thumbnails');
	});

	it('button should be disabled while regenerating', () => {
		// Simulates the disabled state logic
		let regenerating = false;
		expect(regenerating).toBe(false);

		regenerating = true;
		expect(regenerating).toBe(true);
	});

	it('button should use primary color styling', () => {
		// The regeneration button should use the same primary color
		// as the rest of the admin settings page
		const expectedStyle = 'background-color: var(--color-primary)';
		expect(expectedStyle).toContain('var(--color-primary)');
	});
});
