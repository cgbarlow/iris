/**
 * SPEC-205-b / v6.30.0: smart-markdown companion panel — fillable
 * token extraction + source rewrite.
 *
 * Per repo testing posture: data-shape + business-rule tests.
 */

import { describe, expect, it } from 'vitest';

// Mirror of FILLABLE_RE in SmartMarkdownCompanionPanel.svelte.
const FILLABLE_RE = /\{\{element:([^:}]+):attr:([^=}]+)=\}\}/g;

interface Match {
	start: number;
	end: number;
	elementId: string;
	attrPath: string;
}

function findFillable(source: string): Match[] {
	const out: Match[] = [];
	FILLABLE_RE.lastIndex = 0;
	let m: RegExpExecArray | null;
	while ((m = FILLABLE_RE.exec(source)) !== null) {
		out.push({
			start: m.index,
			end: m.index + m[0].length,
			elementId: m[1],
			attrPath: m[2],
		});
	}
	return out;
}

function applyValue(source: string, tok: Match, raw: string): string {
	const safe = raw.replace(/[\\}]/g, '').trim();
	if (!safe) return source;
	const before = source.substring(0, tok.start);
	const after = source.substring(tok.end);
	const newToken = source
		.substring(tok.start, tok.end)
		.replace(/=\}\}$/, `=${safe}}}`);
	return before + newToken + after;
}

describe('fillable-token extraction', () => {
	it('finds an empty-override token', () => {
		const src =
			'- {{element:abc:attr:attributes/Quantity/type=}} of broccoli';
		const matches = findFillable(src);
		expect(matches).toHaveLength(1);
		expect(matches[0].elementId).toBe('abc');
		expect(matches[0].attrPath).toBe('attributes/Quantity/type');
	});

	it('ignores tokens that already have a value', () => {
		const src = '{{element:abc:attr:attributes/Quantity/type=500}}';
		expect(findFillable(src)).toHaveLength(0);
	});

	it('ignores non-attr tokens', () => {
		const src = '{{element:abc:name}}';
		expect(findFillable(src)).toHaveLength(0);
	});

	it('finds multiple fillable tokens in one source', () => {
		const src =
			'- {{element:abc:attr:attributes/Quantity/type=}} g pork\n' +
			'- {{element:def:attr:attributes/Quantity/type=}} ml butter';
		const matches = findFillable(src);
		expect(matches).toHaveLength(2);
		expect(matches[0].elementId).toBe('abc');
		expect(matches[1].elementId).toBe('def');
	});

	it('matches at different byte positions for identical tokens', () => {
		const src =
			'{{element:abc:attr:attributes/Quantity/type=}} ' +
			'{{element:abc:attr:attributes/Quantity/type=}}';
		const matches = findFillable(src);
		expect(matches).toHaveLength(2);
		expect(matches[0].start).not.toEqual(matches[1].start);
	});
});

describe('applyValue rewrite', () => {
	it('rewrites the source at the right byte position', () => {
		const src =
			'- {{element:abc:attr:attributes/Quantity/type=}} g pork';
		const tok = findFillable(src)[0];
		const next = applyValue(src, tok, '500');
		expect(next).toBe(
			'- {{element:abc:attr:attributes/Quantity/type=500}} g pork',
		);
	});

	it('disambiguates duplicate fillable tokens by index', () => {
		const src =
			'A {{element:abc:attr:attributes/Quantity/type=}} ' +
			'B {{element:abc:attr:attributes/Quantity/type=}}';
		const matches = findFillable(src);
		// Fill only the SECOND occurrence.
		const next = applyValue(src, matches[1], '999');
		expect(next).toBe(
			'A {{element:abc:attr:attributes/Quantity/type=}} ' +
			'B {{element:abc:attr:attributes/Quantity/type=999}}',
		);
		// First occurrence untouched.
		expect(next.indexOf('=}}')).toBe(
			'A {{element:abc:attr:attributes/Quantity/type'.length,
		);
	});

	it('empty value is a no-op (does not strip the =)', () => {
		const src =
			'- {{element:abc:attr:attributes/Quantity/type=}}';
		const tok = findFillable(src)[0];
		expect(applyValue(src, tok, '')).toBe(src);
		expect(applyValue(src, tok, '   ')).toBe(src);
	});

	it('strips } and \\ from input to avoid mangling', () => {
		const src =
			'- {{element:abc:attr:attributes/X/type=}}';
		const tok = findFillable(src)[0];
		// Trying to break out of the token via `}` would mangle the source.
		const next = applyValue(src, tok, 'val}}injection');
		expect(next).toBe(
			'- {{element:abc:attr:attributes/X/type=valinjection}}',
		);
	});

	it('values with internal whitespace are preserved', () => {
		const src = '{{element:abc:attr:attributes/X/type=}}';
		const tok = findFillable(src)[0];
		// The trim() in applyValue trims edges, not internal whitespace.
		const next = applyValue(src, tok, ' 1 cup ');
		expect(next).toBe('{{element:abc:attr:attributes/X/type=1 cup}}');
	});
});

describe('humanise attribute path', () => {
	function humaniseAttrPath(attrPath: string): string {
		const segs = attrPath.split('/').filter(Boolean);
		if (segs[0] === 'attributes' && segs.length >= 2) return segs[1];
		return attrPath;
	}

	it('extracts the attribute name from attributes/<NAME>/type', () => {
		expect(humaniseAttrPath('attributes/Quantity/type')).toBe('Quantity');
		expect(humaniseAttrPath('attributes/Unit/notes')).toBe('Unit');
	});

	it('falls back to the raw path for non-standard shapes', () => {
		expect(humaniseAttrPath('topLevel/type')).toBe('topLevel/type');
		expect(humaniseAttrPath('name')).toBe('name');
	});
});
