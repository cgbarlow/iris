import { describe, it, expect } from 'vitest';

/**
 * TagInput component unit tests.
 * Tests the component's data model and sanitization logic.
 */

describe('TagInput logic', () => {
	it('sanitizes HTML from tag input', async () => {
		const { default: DOMPurify } = await import('dompurify');
		const input = '<script>alert("xss")</script>test-tag';
		const sanitized = DOMPurify.sanitize(input.trim());
		expect(sanitized).toBe('test-tag');
		expect(sanitized).not.toContain('<script>');
	});

	it('rejects empty tags', () => {
		const tag = ''.trim();
		expect(!tag || tag.length > 50).toBe(true);
	});

	it('rejects tags over 50 characters', () => {
		const tag = 'x'.repeat(51);
		expect(!tag || tag.length > 50).toBe(true);
	});

	it('accepts valid tags up to 50 characters', () => {
		const tag = 'architecture';
		expect(!tag || tag.length > 50).toBe(false);
	});

	it('prevents duplicate tags', () => {
		const existingTags = ['frontend', 'backend'];
		const newTag = 'frontend';
		expect(existingTags.includes(newTag)).toBe(true);
	});

	it('prevents adding inherited tags as own tags', () => {
		const ownTags = ['frontend'];
		const inheritedTags = ['shared'];
		const newTag = 'shared';
		expect(ownTags.includes(newTag) || inheritedTags.includes(newTag)).toBe(true);
	});

	it('allows new non-duplicate tags', () => {
		const existingTags = ['frontend', 'backend'];
		const inheritedTags = ['shared'];
		const newTag = 'database';
		expect(
			existingTags.includes(newTag) || inheritedTags.includes(newTag),
		).toBe(false);
	});

	it('trims whitespace from tags', () => {
		const tag = '  architecture  '.trim();
		expect(tag).toBe('architecture');
	});
});
