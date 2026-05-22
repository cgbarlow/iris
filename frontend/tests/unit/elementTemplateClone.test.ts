/**
 * SPEC-211-e / v6.29.0: element-template clone request body shape.
 *
 * Per repo testing posture: data-shape tests, not full component
 * renders.
 */

import { describe, expect, it } from 'vitest';

interface CloneSource {
	id: string;
	name: string;
	description: string | null;
	is_global: boolean;
	markdown_stamp?: string | null;
	template_data: Record<string, unknown>;
}

/**
 * Mirrors the body-construction logic in
 * `frontend/src/routes/elements/+page.svelte::confirmCloneTemplate`.
 */
function buildCloneBody(
	source: CloneSource,
	newName: string,
	currentSetId: string,
): Record<string, unknown> {
	const body: Record<string, unknown> = {
		name: newName.trim(),
		description: source.description,
		template_data: source.template_data,
		is_global: source.is_global,
		set_id: source.is_global ? null : currentSetId,
	};
	if (source.markdown_stamp) {
		body.markdown_stamp = source.markdown_stamp;
	}
	return body;
}

describe('POST /api/element-templates — clone body shape', () => {
	it('includes markdown_stamp when source has one', () => {
		const body = buildCloneBody({
			id: 's', name: 'Ingredient', description: 'desc',
			is_global: true,
			markdown_stamp: '{{self:attr:attributes/Quantity/type=}}',
			template_data: { element_type: 'class' },
		}, 'My ingredient', 'set-A');
		expect(body.markdown_stamp).toBe(
			'{{self:attr:attributes/Quantity/type=}}',
		);
	});

	it('omits markdown_stamp when source has none', () => {
		const body = buildCloneBody({
			id: 's', name: 'Plain', description: null,
			is_global: true, template_data: {},
		}, 'Copy', 'set-A');
		expect('markdown_stamp' in body).toBe(false);
	});

	it('clone of global → still global (set_id null)', () => {
		const body = buildCloneBody({
			id: 's', name: 'G', description: null, is_global: true,
			template_data: {},
		}, 'G2', 'set-A');
		expect(body.is_global).toBe(true);
		expect(body.set_id).toBeNull();
	});

	it('clone of set-scoped → set-scoped in current set', () => {
		const body = buildCloneBody({
			id: 's', name: 'S', description: null, is_global: false,
			template_data: {},
		}, 'S2', 'set-A');
		expect(body.is_global).toBe(false);
		expect(body.set_id).toBe('set-A');
	});

	it('default name suffix is " (copy)"', () => {
		const defaultName = (source: CloneSource) => `${source.name} (copy)`;
		expect(defaultName({
			id: 's', name: 'Ingredient', description: null,
			is_global: true, template_data: {},
		})).toBe('Ingredient (copy)');
	});

	it('description is preserved verbatim', () => {
		const body = buildCloneBody({
			id: 's', name: 'X', description: 'A specific blurb',
			is_global: true, template_data: {},
		}, 'X2', 'set-A');
		expect(body.description).toBe('A specific blurb');
	});
});
