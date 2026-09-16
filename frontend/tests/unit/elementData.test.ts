/**
 * ADR-243 / SPEC-243-A: element `data` panel helpers (issue #292).
 *
 * Pure-function tests for `extraDataEntries`, which turns an element's
 * `data` blob into the read-only rows shown in the element page's
 * **Data** accordion — every key the page does not already render
 * elsewhere (i.e. everything except a UML `attributes` array).
 *
 * ADR-245: `toDataEditRows` / `applyDataEditRows` back the same panel's
 * edit mode — typed rows in, validated `data` out.
 */

import { describe, expect, it } from 'vitest';

import { applyDataEditRows, extraDataEntries, toDataEditRows } from '$lib/utils/elementData';

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

describe('toDataEditRows', () => {
	it('returns no rows for missing or non-object data', () => {
		expect(toDataEditRows(undefined)).toEqual([]);
		expect(toDataEditRows([1])).toEqual([]);
	});

	it('maps each value to a typed row, skipping an attributes array', () => {
		expect(
			toDataEditRows({
				attributes: [{ name: 'id' }],
				publication: 'Uncharted Quests',
				part: 2,
				draft: false,
				reviewer: null,
				links: { canonical: '/a' },
			}),
		).toEqual([
			{ key: 'publication', type: 'text', value: 'Uncharted Quests' },
			{ key: 'part', type: 'number', value: '2' },
			{ key: 'draft', type: 'boolean', value: 'false' },
			{ key: 'reviewer', type: 'json', value: 'null' },
			{ key: 'links', type: 'json', value: '{\n  "canonical": "/a"\n}' },
		]);
	});

	it('keeps a non-array attributes value as an editable row', () => {
		expect(toDataEditRows({ attributes: 'colour' })).toEqual([
			{ key: 'attributes', type: 'text', value: 'colour' },
		]);
	});
});

describe('applyDataEditRows', () => {
	const noAttrs = { attributesArrayInUse: false };

	it('round-trips toDataEditRows output back to the same values', () => {
		const data = {
			type: 'article',
			part: 2,
			weight: -1.5,
			draft: true,
			reviewer: null,
			links: { canonical: '/a', tags: ['x'] },
		};
		expect(applyDataEditRows(toDataEditRows(data), noAttrs)).toEqual({ ok: true, data });
	});

	it('trims keys, drops fully blank rows, and follows row order', () => {
		expect(
			applyDataEditRows(
				[
					{ key: ' b ', type: 'text', value: ' spaced ' },
					{ key: '', type: 'text', value: '' },
					{ key: 'a', type: 'number', value: ' 3 ' },
				],
				noAttrs,
			),
		).toEqual({ ok: true, data: { b: ' spaced ', a: 3 } });
	});

	it('allows an empty text value', () => {
		expect(applyDataEditRows([{ key: 'note', type: 'text', value: '' }], noAttrs)).toEqual({
			ok: true,
			data: { note: '' },
		});
	});

	it('rejects a value without a key', () => {
		expect(applyDataEditRows([{ key: '  ', type: 'text', value: 'orphan' }], noAttrs)).toEqual({
			ok: false,
			error: 'Data row 1 needs a key',
		});
	});

	it('rejects duplicate keys', () => {
		const rows = [
			{ key: 'slug', type: 'text' as const, value: 'a' },
			{ key: 'slug', type: 'text' as const, value: 'b' },
		];
		expect(applyDataEditRows(rows, noAttrs)).toEqual({
			ok: false,
			error: 'Data key "slug" is used more than once',
		});
	});

	it('rejects an attributes key only while the Attributes table owns it', () => {
		const rows = [{ key: 'attributes', type: 'text' as const, value: 'x' }];
		expect(applyDataEditRows(rows, { attributesArrayInUse: true })).toEqual({
			ok: false,
			error: 'Data key "attributes" is reserved for the Attributes table',
		});
		expect(applyDataEditRows(rows, noAttrs)).toEqual({ ok: true, data: { attributes: 'x' } });
	});

	it('rejects invalid numbers, booleans, and JSON', () => {
		expect(applyDataEditRows([{ key: 'n', type: 'number', value: 'two' }], noAttrs)).toEqual({
			ok: false,
			error: 'Data "n" must be a number',
		});
		expect(applyDataEditRows([{ key: 'n', type: 'number', value: ' ' }], noAttrs)).toEqual({
			ok: false,
			error: 'Data "n" must be a number',
		});
		expect(applyDataEditRows([{ key: 'b', type: 'boolean', value: 'yes' }], noAttrs)).toEqual({
			ok: false,
			error: 'Data "b" must be true or false',
		});
		expect(applyDataEditRows([{ key: 'j', type: 'json', value: '{oops' }], noAttrs)).toEqual({
			ok: false,
			error: 'Data "j" is not valid JSON',
		});
	});
});
