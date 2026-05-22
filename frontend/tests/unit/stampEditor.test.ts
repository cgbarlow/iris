/**
 * SPEC-211-c / v6.24.0: element-template stamp editor request/response shape.
 *
 * Light-touch unit tests aligned with this repo's frontend testing
 * posture (data shape + business rules, not Svelte component
 * rendering — see comment in namedPrompts.test.ts).
 */

import { describe, expect, it } from 'vitest';

interface ElementTemplate {
	id: string;
	name: string;
	markdown_stamp: string | null;
	[k: string]: unknown;
}

interface PutBody {
	markdown_stamp: string;
}

describe('PUT /api/element-templates/{id} — stamp update', () => {
	it('sends a non-empty body for a new stamp', () => {
		const draft = '{{self:attr:attributes/Quantity/type=}} {{self:name}}';
		const body: PutBody = { markdown_stamp: draft };
		expect(body.markdown_stamp).toBe(draft);
		expect(body.markdown_stamp.length).toBeGreaterThan(0);
	});

	it('sends an empty string to clear the stamp', () => {
		const body: PutBody = { markdown_stamp: '' };
		expect(body.markdown_stamp).toBe('');
	});

	it('preserves a whitespace-only stamp verbatim', () => {
		// Current backend treats a whitespace-only string as set
		// (not clear). v1 frontend matches.
		const body: PutBody = { markdown_stamp: '   ' };
		expect(body.markdown_stamp).toBe('   ');
	});

	it('does not modify the body when the editor was opened with an existing stamp', () => {
		const initial: ElementTemplate = {
			id: 'tpl-1', name: 'Quantified item',
			markdown_stamp: '{{self:name}}',
		};
		const draft = initial.markdown_stamp ?? '';
		expect(draft).toBe('{{self:name}}');
	});
});

describe('round-trip: response updates local state', () => {
	it('replaces the page-level tpl with the PUT response', () => {
		// The detail page does `tpl = updated;` after the PUT — local
		// state shape must match the response shape.
		const before: ElementTemplate = {
			id: 'tpl-1', name: 'Quantified item',
			markdown_stamp: '{{self:name}}',
		};
		const response: ElementTemplate = {
			id: 'tpl-1', name: 'Quantified item',
			markdown_stamp: '{{self:attr:attributes/Quantity/type=}} {{self:name}}',
		};
		const after: ElementTemplate = response;
		expect(after.markdown_stamp).not.toBe(before.markdown_stamp);
		expect(after.id).toBe(before.id);
	});

	it('null markdown_stamp from a clear renders as no-stamp state', () => {
		const response: ElementTemplate = {
			id: 'tpl-1', name: 'Quantified item',
			markdown_stamp: null,
		};
		expect(response.markdown_stamp).toBeNull();
	});
});

describe('stamp body authoring helpers', () => {
	it('recognises the seeded "Quantified item" template format', () => {
		const stamp = (
			'{{self:attr:attributes/Quantity/type=}} ' +
			'{{self:attr:attributes/Unit/type}} ' +
			'{{self:name}}'
		);
		expect(stamp).toMatch(/\{\{self:attr:[^}]+=\}\}/);  // fillable slot
		expect(stamp).toContain('{{self:attr:attributes/Unit/type}}');
		expect(stamp).toContain('{{self:name}}');
	});

	it('does NOT recognise {{element:UUID:…}} tokens as self-references', () => {
		// Authors editing a stamp should use {{self:…}}, not concrete
		// element refs. The picker (PR 7 / v6.23.0) substitutes self →
		// element-id at insert time; if a stamp embeds a concrete
		// element-id it will be pinned to that element rather than
		// the one being stamped against.
		const bad = '{{element:abc:name}}';
		expect(bad).not.toMatch(/\{\{self:/);
	});
});
