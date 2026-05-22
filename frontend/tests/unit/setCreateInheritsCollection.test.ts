/**
 * SPEC-216-a / v6.28.0: set creation inherits active collection.
 *
 * Per repo testing posture: data-shape + business-rule tests rather
 * than full Svelte component renders.
 */

import { describe, expect, it } from 'vitest';

/**
 * Mirrors the body-construction logic in
 * `frontend/src/routes/sets/+page.svelte::handleCreate`.
 */
function buildCreateSetBody(
	name: string,
	description: string | null,
	collectionId: string,
): Record<string, unknown> {
	const body: Record<string, unknown> = { name, description };
	if (collectionId) {
		body.collection_id = collectionId;
	}
	return body;
}

describe('POST /api/sets body construction', () => {
	it('includes collection_id when the active filter is set', () => {
		const body = buildCreateSetBody('Groceries', null, 'col-123');
		expect(body).toEqual({
			name: 'Groceries',
			description: null,
			collection_id: 'col-123',
		});
	});

	it('omits collection_id when no active filter', () => {
		const body = buildCreateSetBody('Misc', 'A grab-bag', '');
		expect(body).toEqual({
			name: 'Misc',
			description: 'A grab-bag',
		});
		expect('collection_id' in body).toBe(false);
	});

	it('preserves the description value verbatim', () => {
		const body = buildCreateSetBody('S', 'with description', 'c');
		expect(body.description).toBe('with description');
	});

	it('does not coerce empty collectionId into null (omits key)', () => {
		const body = buildCreateSetBody('S', null, '');
		// Backend behaviour treats absent key === collection_id=null.
		// The frontend omits, doesn't send null.
		expect('collection_id' in body).toBe(false);
	});
});
