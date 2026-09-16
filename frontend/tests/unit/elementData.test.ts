/**
 * ADR-243 / SPEC-243-A: element `data` panel helpers (issue #292).
 *
 * Pure-function tests for `extraDataEntries`, which turns an element's
 * `data` blob into the read-only rows shown in the element page's
 * **Data** accordion — every key the page does not already render
 * elsewhere (i.e. everything except a UML `attributes` array).
 */

import { describe, expect, it } from 'vitest';

import { extraDataEntries } from '$lib/utils/elementData';

describe('extraDataEntries', () => {
	it('returns no rows for missing, null, or non-object data', () => {
		expect(extraDataEntries(undefined)).toEqual([]);
		expect(extraDataEntries(null)).toEqual([]);
		expect(extraDataEntries('text')).toEqual([]);
		expect(extraDataEntries(42)).toEqual([]);
		expect(extraDataEntries([1, 2])).toEqual([]);
		expect(extraDataEntries({})).toEqual([]);
	});

	it('renders the issue #292 article payload as scalar rows in authored order', () => {
		const rows = extraDataEntries({
			type: 'article',
			slug: 'epic-quest-career-development-part-2',
			url: 'https://unchartedquests.substack.com/p/an-epic-quest-in-career-development-d1a',
			publication: 'Uncharted Quests',
			date: '2025-03-16',
			series: 'An epic quest in career development',
			part: 2,
		});
		expect(rows.map((r) => r.key)).toEqual([
			'type',
			'slug',
			'url',
			'publication',
			'date',
			'series',
			'part',
		]);
		expect(rows.every((r) => r.kind === 'text')).toBe(true);
		expect(rows.find((r) => r.key === 'part')).toEqual({ key: 'part', kind: 'text', value: '2' });
	});

	it('excludes an `attributes` array, which the Attributes accordion already renders', () => {
		const rows = extraDataEntries({
			attributes: [{ name: 'id', type: 'int' }],
			owner: 'Platform team',
		});
		expect(rows).toEqual([{ key: 'owner', kind: 'text', value: 'Platform team' }]);
	});

	it('keeps a non-array `attributes` value, since no other panel can show it', () => {
		const rows = extraDataEntries({ attributes: 'colour, size' });
		expect(rows).toEqual([{ key: 'attributes', kind: 'text', value: 'colour, size' }]);
	});

	it('stringifies booleans, numbers, and null', () => {
		expect(extraDataEntries({ draft: false, weight: 1.5, reviewer: null })).toEqual([
			{ key: 'draft', kind: 'text', value: 'false' },
			{ key: 'weight', kind: 'text', value: '1.5' },
			{ key: 'reviewer', kind: 'text', value: 'null' },
		]);
	});

	it('renders nested objects and arrays as pretty-printed JSON', () => {
		const rows = extraDataEntries({ tags: ['a', 'b'], author: { name: 'Sam' } });
		expect(rows).toEqual([
			{ key: 'tags', kind: 'json', value: '[\n  "a",\n  "b"\n]' },
			{ key: 'author', kind: 'json', value: '{\n  "name": "Sam"\n}' },
		]);
	});

	it('links only http(s) URLs', () => {
		const [https, http, js, relative] = extraDataEntries({
			a: 'https://example.com/x?y=1',
			b: 'HTTP://example.com',
			c: 'javascript:alert(1)',
			d: '/elements/123',
		});
		expect(https.href).toBe('https://example.com/x?y=1');
		expect(http.href).toBe('HTTP://example.com');
		expect(js.href).toBeUndefined();
		expect(relative.href).toBeUndefined();
	});

	it('does not link a string that merely contains a URL', () => {
		const [row] = extraDataEntries({ note: 'see https://example.com for more' });
		expect(row.href).toBeUndefined();
	});
});
