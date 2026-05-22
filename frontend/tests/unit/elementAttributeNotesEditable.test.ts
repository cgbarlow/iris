/**
 * v6.30.1 fix: element edit-mode UML attribute table now has a Notes
 * column (the browse view already showed it; the editor was missing
 * the input — values would be silently dropped on Save).
 *
 * Light-touch data-shape test: mirrors the edit-state mapping in
 * `frontend/src/routes/elements/[id]/+page.svelte::startEdit` and
 * the save-back flow.
 */

import { describe, expect, it } from 'vitest';

interface RawAttribute {
	name?: string;
	type?: string;
	scope?: string;
	notes?: string;
	lower_bound?: string;
	upper_bound?: string;
}

interface EditAttribute {
	name: string;
	type: string;
	scope: string;
	notes: string;
	lower_bound: string;
	upper_bound: string;
}

function toEditState(src: RawAttribute[]): EditAttribute[] {
	return src.map((a) => ({
		name: a.name ?? '',
		type: a.type ?? '',
		scope: a.scope ?? 'Public',
		notes: a.notes ?? '',
		lower_bound: a.lower_bound ?? '',
		upper_bound: a.upper_bound ?? '',
	}));
}

function toSaveBody(edit: EditAttribute[]): EditAttribute[] {
	// Mirror of `updatedData.attributes = editAttributes.filter(a => a.name.trim())`.
	return edit.filter((a) => a.name.trim());
}

describe('UML attribute notes round-trip', () => {
	it('preserves notes from stored data into the edit state', () => {
		const src: RawAttribute[] = [
			{ name: 'Quantity', type: 'g', scope: 'Public', notes: 'per use override' },
		];
		const edit = toEditState(src);
		expect(edit[0].notes).toBe('per use override');
	});

	it('defaults missing notes to empty string', () => {
		const src: RawAttribute[] = [
			{ name: 'X', type: '' },
		];
		const edit = toEditState(src);
		expect(edit[0].notes).toBe('');
	});

	it('save-back body carries the (possibly edited) notes value', () => {
		const edit: EditAttribute[] = [
			{
				name: 'Quantity', type: 'g', scope: 'Public',
				notes: 'edited via the new column',
				lower_bound: '', upper_bound: '',
			},
		];
		const body = toSaveBody(edit);
		expect(body[0].notes).toBe('edited via the new column');
	});

	it('empty-name rows are filtered out on save (existing behaviour)', () => {
		const edit: EditAttribute[] = [
			{ name: 'A', type: '', scope: 'Public', notes: 'keeps notes',
			  lower_bound: '', upper_bound: '' },
			{ name: '', type: '', scope: 'Public', notes: 'drops the row',
			  lower_bound: '', upper_bound: '' },
		];
		const body = toSaveBody(edit);
		expect(body).toHaveLength(1);
		expect(body[0].name).toBe('A');
	});
});
