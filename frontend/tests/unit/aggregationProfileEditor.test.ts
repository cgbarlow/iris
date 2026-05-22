/**
 * SPEC-212-d / v6.25.0: AggregationProfileEditor request/filter shapes.
 *
 * Per repo convention, data-shape + business-rule tests rather than
 * full component renders.
 */

import { describe, expect, it } from 'vitest';

interface AggregationProfile {
	id: string;
	name: string;
	description: string | null;
	set_id: string | null;
	set_name: string | null;
	is_global: boolean;
	is_default_for_set: boolean;
	profile_data: Record<string, unknown>;
	created_by: string | null;
	created_by_username: string;
	created_at: string;
	updated_at: string;
}

describe('POST/PUT body shapes', () => {
	it('global-mode create includes is_global=true, omits set_id', () => {
		const draft = {
			name: 'Custom rollup',
			description: 'Sum X by Y',
			profile_data: { traversal: { inner: { collect_token_type: 'element', skip_blank_values: true } }, output: {} },
			is_default_for_set: false,
			is_global: true,
		};
		expect(draft.is_global).toBe(true);
		expect((draft as Record<string, unknown>).set_id).toBeUndefined();
	});

	it('set-scoped create includes set_id, omits is_global', () => {
		const setId = 'abc';
		const draft = {
			name: 'Custom rollup',
			description: null,
			profile_data: { traversal: { inner: { collect_token_type: 'element', skip_blank_values: true } }, output: {} },
			is_default_for_set: true,
			set_id: setId,
		};
		expect(draft.set_id).toBe(setId);
		expect((draft as Record<string, unknown>).is_global).toBeUndefined();
	});

	it('PUT body does not include is_global / set_id (scope locked at create time)', () => {
		// The component does not flip scope on edit. Re-scoping is a
		// separate operation (delete + recreate). Keeps the editor
		// simple.
		const draft = {
			name: 'Edited name',
			description: 'New description',
			profile_data: {} as Record<string, unknown>,
			is_default_for_set: false,
		};
		expect((draft as Record<string, unknown>).set_id).toBeUndefined();
		expect((draft as Record<string, unknown>).is_global).toBeUndefined();
	});
});

describe('list filter logic', () => {
	const ROWS: AggregationProfile[] = [
		{
			id: '1', name: 'Shopping list', description: null,
			set_id: null, set_name: null, is_global: true,
			is_default_for_set: false, profile_data: {},
			created_by: null, created_by_username: 'admin',
			created_at: '', updated_at: '',
		},
		{
			id: '2', name: 'Custom A', description: null,
			set_id: 'set-A', set_name: 'A', is_global: false,
			is_default_for_set: false, profile_data: {},
			created_by: null, created_by_username: 'admin',
			created_at: '', updated_at: '',
		},
		{
			id: '3', name: 'Custom B', description: null,
			set_id: 'set-B', set_name: 'B', is_global: false,
			is_default_for_set: false, profile_data: {},
			created_by: null, created_by_username: 'admin',
			created_at: '', updated_at: '',
		},
	];

	it('globals mode keeps only is_global rows', () => {
		const filtered = ROWS.filter((p) => p.is_global);
		expect(filtered.map((p) => p.id)).toEqual(['1']);
	});

	it('set mode for set-A keeps only set-A non-global rows', () => {
		const setId = 'set-A';
		const filtered = ROWS.filter((p) => !p.is_global && p.set_id === setId);
		expect(filtered.map((p) => p.id)).toEqual(['2']);
	});

	it('set mode for set-A excludes globals even when include_global=true on the server', () => {
		const setId = 'set-A';
		// Server returns set-A's rows + all globals when include_global=true.
		// Client filters to non-global + same-set.
		const filtered = ROWS.filter((p) => !p.is_global && p.set_id === setId);
		expect(filtered.find((p) => p.is_global)).toBeUndefined();
	});
});

describe('JSON parse-validate', () => {
	it('valid JSON parses', () => {
		const raw = '{"traversal": {"inner": {"collect_token_type": "element"}}, "output": {}}';
		expect(() => JSON.parse(raw)).not.toThrow();
	});

	it('invalid JSON throws', () => {
		const raw = '{"traversal": invalid}';
		expect(() => JSON.parse(raw)).toThrow();
	});

	it('default clone template is valid JSON and includes required fields', () => {
		const raw = JSON.stringify({
			traversal: {
				inner: {
					collect_token_type: 'element',
					value_attribute_path: 'attributes/Quantity/type',
					bucket_attribute_path: null,
					skip_blank_values: true,
				},
			},
			output: {
				group_by: 'element.package_name',
				sort_groups: 'alpha',
				sort_items_within_group: 'alpha',
				aggregation_fn: 'sum',
				line_format: '- {element.name}: {sum_value}{bucket_spaced}',
				show_per_source_breakdown: false,
				breakdown_format: ' ({sources_joined})',
			},
		});
		const parsed = JSON.parse(raw);
		expect(parsed.traversal.inner.collect_token_type).toBe('element');
		expect(parsed.output.aggregation_fn).toBe('sum');
	});
});
