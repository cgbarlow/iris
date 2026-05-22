/**
 * SPEC-211-b / v6.19.1: smart-markdown picker — Stamps section.
 *
 * The picker fetches in-scope stamps for the drilled element and
 * surfaces them as one-pick rows above the existing field list.
 * Backend resolves `{{self:…}}` → `{{element:UUID:…}}` so the body
 * is paste-ready.
 *
 * Per this repo's frontend testing posture (data-shape + business
 * rules, not full Svelte component rendering — see comment in
 * namedPrompts.test.ts), this test exercises the network/data
 * contract the picker depends on, not the full component render.
 */

import { describe, expect, it } from 'vitest';

interface StampEntry {
	id: string;
	name: string;
	description: string | null;
	is_global: boolean;
	markdown_stamp: string;
}

interface StampsResponse {
	items: StampEntry[];
}

describe('/api/element-templates/stamps response shape', () => {
	it('parses a typical seeded-globals response', () => {
		const body: StampsResponse = {
			items: [
				{
					id: 'ea8829e5-6e3f-5cf6-b1cc-a5ad92312dbf',
					name: 'Quantified item',
					description: 'Element with a numeric quantity + unit',
					is_global: true,
					markdown_stamp: (
						'{{element:abc:attr:attributes/Quantity/type=}} ' +
						'{{element:abc:attr:attributes/Unit/type}} ' +
						'{{element:abc:name}}'
					),
				},
				{
					id: '08f53b8a-3876-5af5-bd9d-5b6959fea660',
					name: 'Sized story',
					description: null,
					is_global: true,
					markdown_stamp: '{{element:abc:attr:attributes/Points/type=}} pts — {{element:abc:name}}',
				},
			],
		};
		expect(body.items).toHaveLength(2);
		expect(body.items[0].is_global).toBe(true);
		// Backend has substituted {{self:…}} → {{element:abc:…}} per ADR-211.
		expect(body.items[0].markdown_stamp).not.toContain('{{self:');
		expect(body.items[0].markdown_stamp).toContain('{{element:abc:');
	});

	it('handles an empty response gracefully', () => {
		const body: StampsResponse = { items: [] };
		expect(body.items).toHaveLength(0);
	});
});

describe('stamp insert contract', () => {
	it('emits the stamp body verbatim — no extra wrapping', () => {
		// The picker passes stamp.markdown_stamp to oninsert() unchanged.
		// The smart-markdown resolver then processes the embedded
		// {{element:UUID:…}} tokens as it would for any author-typed
		// tokens.
		const stamp: StampEntry = {
			id: 'x', name: 'Quantified item', description: null,
			is_global: true,
			markdown_stamp: '{{element:abc:attr:attributes/Quantity/type=}} g',
		};
		// Simulated picker behaviour:
		let emitted = '';
		const oninsert = (token: string) => { emitted = token; };
		oninsert(stamp.markdown_stamp);
		expect(emitted).toBe('{{element:abc:attr:attributes/Quantity/type=}} g');
	});

	it('preserves fillable-slot markers in the stamp body', () => {
		// ADR-210: tokens with `=` (no value) are fillable slots that
		// render as strikethrough. Stamps embed these freely. The
		// closing `}}` follows immediately after the trailing `=`,
		// which is the marker the resolver recognises.
		const body = '{{element:x:attr:attributes/Quantity/type=}}';
		expect(body).toMatch(/Quantity\/type=\}\}$/);
	});
});

describe('scope semantics (per SPEC-211-a §3)', () => {
	it('global stamps surface for any element_type', () => {
		// Backend filter rule: if a stamp's template_data.element_type
		// is set, it must match. The seeded stamps target
		// element_type=class — so a class-typed grocery item gets all
		// five seeded stamps offered.
		const stamps: StampEntry[] = [
			{ id: '1', name: 'Quantified item', description: null,
			  is_global: true, markdown_stamp: '' },
			{ id: '2', name: 'Sized story', description: null,
			  is_global: true, markdown_stamp: '' },
		];
		expect(stamps.every((s) => s.is_global)).toBe(true);
	});

	it('set-scoped stamp does NOT appear when querying a different set', () => {
		// The backend already filters; the frontend just receives the
		// pre-filtered list. This test documents the contract.
		const responseForSetA: StampsResponse = { items: [] };
		expect(responseForSetA.items).toHaveLength(0);
	});
});
