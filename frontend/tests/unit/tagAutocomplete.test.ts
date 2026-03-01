import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Tag autocomplete tests (WP-10).
 * Verifies TagInput component supports suggestions prop with
 * filtered dropdown, keyboard navigation, and ARIA attributes.
 */

describe('TagInput autocomplete', () => {
	const tagInputSrc = readFileSync(
		resolve(__dirname, '../../src/lib/components/TagInput.svelte'),
		'utf-8',
	);

	it('accepts suggestions prop', () => {
		expect(tagInputSrc).toContain('suggestions');
	});

	it('computes filteredSuggestions from input and suggestions', () => {
		expect(tagInputSrc).toContain('filteredSuggestions');
	});

	it('filters out already-applied tags from suggestions', () => {
		expect(tagInputSrc).toContain('!tags.includes(s)');
	});

	it('filters out inherited tags from suggestions', () => {
		expect(tagInputSrc).toContain('!inheritedTags.includes(s)');
	});

	it('supports keyboard navigation with ArrowDown and ArrowUp', () => {
		expect(tagInputSrc).toContain("event.key === 'ArrowDown'");
		expect(tagInputSrc).toContain("event.key === 'ArrowUp'");
	});

	it('supports Enter to select suggestion', () => {
		expect(tagInputSrc).toContain("event.key === 'Enter'");
		expect(tagInputSrc).toContain('selectSuggestion');
	});

	it('supports Escape to close suggestions', () => {
		expect(tagInputSrc).toContain("event.key === 'Escape'");
	});

	it('uses combobox ARIA role', () => {
		expect(tagInputSrc).toContain('role="combobox"');
		expect(tagInputSrc).toContain('aria-expanded');
		expect(tagInputSrc).toContain('aria-autocomplete="list"');
	});

	it('renders suggestion list with listbox role', () => {
		expect(tagInputSrc).toContain('role="listbox"');
		expect(tagInputSrc).toContain('role="option"');
	});

	it('sanitizes input with DOMPurify', () => {
		expect(tagInputSrc).toContain('DOMPurify.sanitize');
	});
});

describe('Entity page passes suggestions to TagInput', () => {
	const entityPageSrc = readFileSync(
		resolve(__dirname, '../../src/routes/entities/[id]/+page.svelte'),
		'utf-8',
	);

	it('fetches all tags for suggestions', () => {
		expect(entityPageSrc).toContain('/api/entities/tags/all');
	});

	it('passes suggestions prop to TagInput', () => {
		expect(entityPageSrc).toContain('suggestions={allTags}');
	});
});

describe('Model page passes suggestions to TagInput', () => {
	const modelPageSrc = readFileSync(
		resolve(__dirname, '../../src/routes/models/[id]/+page.svelte'),
		'utf-8',
	);

	it('fetches all tags for suggestions', () => {
		expect(modelPageSrc).toContain('/api/entities/tags/all');
	});

	it('passes suggestions prop to TagInput', () => {
		expect(modelPageSrc).toContain('suggestions={allTags}');
	});
});
