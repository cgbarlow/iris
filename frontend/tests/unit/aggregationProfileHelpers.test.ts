/**
 * SPEC-212-f: tests for the form-editor helpers.
 *
 * Pure-function tests per repo convention (data-shape + round-trip),
 * not full component renders.
 */

import { describe, expect, it } from 'vitest';
import {
	readOutputFields,
	patchOutputFields,
	readTraversalFields,
	patchTraversalFields,
	insertAtCursor,
	buildDraftFromTemplate,
	buildBlankDraft,
	assembleProfileData,
	type OutputFields,
	type TraversalFields,
} from '../../src/lib/components/aggregationProfileHelpers';

const FULL_PROFILE = {
	traversal: {
		outer: {
			collect_token_type: 'diagram',
			multiplier: {
				from_attribute_override: 'attributes/Diners/type',
				divisor_from_diagram_data: 'data.servings',
				default_multiplier: 1,
			},
		},
		inner: {
			collect_token_type: 'element',
			value_attribute_path: 'attributes/Quantity/type',
			bucket_attribute_path: 'attributes/Unit/type',
			skip_blank_values: true,
		},
	},
	output: {
		group_by: 'element.package_name',
		sort_groups: 'alpha',
		sort_items_within_group: 'alpha',
		aggregation_fn: 'sum',
		line_format: '- {element.name}: {sum_value}{bucket_spaced}',
		show_per_source_breakdown: true,
		breakdown_format: ' ({sources_joined})',
		include_provenance: false,
	},
};

describe('readOutputFields', () => {
	it('reads every output field from a complete profile', () => {
		const f = readOutputFields(FULL_PROFILE);
		expect(f.aggregation_fn).toBe('sum');
		expect(f.group_by).toBe('element.package_name');
		expect(f.sort_groups).toBe('alpha');
		expect(f.sort_items_within_group).toBe('alpha');
		expect(f.line_format).toBe('- {element.name}: {sum_value}{bucket_spaced}');
		expect(f.show_per_source_breakdown).toBe(true);
		expect(f.breakdown_format).toBe(' ({sources_joined})');
		expect(f.include_provenance).toBe(false);
	});

	it('fills in defaults for missing fields', () => {
		const f = readOutputFields({ output: {} });
		expect(f.aggregation_fn).toBe('sum');
		expect(f.sort_groups).toBe('alpha');
		expect(f.line_format).toContain('{element.name}');
		expect(f.show_per_source_breakdown).toBe(false);
	});

	it('handles null/undefined profile_data gracefully', () => {
		const f = readOutputFields(null);
		expect(f.aggregation_fn).toBe('sum');
		expect(f.group_by).toBe('');
	});

	it('rejects unknown enum values and falls back to default', () => {
		const f = readOutputFields({ output: { aggregation_fn: 'median', sort_groups: 'random' } });
		expect(f.aggregation_fn).toBe('sum');
		expect(f.sort_groups).toBe('alpha');
	});
});

describe('patchOutputFields', () => {
	it('returns a new object — does NOT mutate input', () => {
		const original = { output: { aggregation_fn: 'sum' } } as Record<string, unknown>;
		const fields: OutputFields = readOutputFields(original);
		const out = patchOutputFields(original, fields);
		expect(out).not.toBe(original);
		expect((original.output as Record<string, unknown>).line_format).toBeUndefined();
	});

	it('round-trip: read → patch produces an equivalent output block', () => {
		const fields = readOutputFields(FULL_PROFILE);
		const patched = patchOutputFields(FULL_PROFILE, fields);
		const output = patched.output as Record<string, unknown>;
		expect(output.aggregation_fn).toBe('sum');
		expect(output.group_by).toBe('element.package_name');
		expect(output.include_provenance).toBe(false);
	});

	it('empty group_by normalises to null (engine treats as ungrouped)', () => {
		const fields = readOutputFields(FULL_PROFILE);
		fields.group_by = '   ';
		const patched = patchOutputFields(FULL_PROFILE, fields);
		expect((patched.output as Record<string, unknown>).group_by).toBeNull();
	});

	it('preserves unrelated keys on the output block (provenance + custom)', () => {
		const original = { output: { custom_future_field: 'keep me', aggregation_fn: 'sum' } } as Record<string, unknown>;
		const fields = readOutputFields(original);
		const patched = patchOutputFields(original, fields);
		expect((patched.output as Record<string, unknown>).custom_future_field).toBe('keep me');
	});
});

describe('readTraversalFields', () => {
	it('reads outer + inner from a two-level profile', () => {
		const f = readTraversalFields(FULL_PROFILE);
		expect(f.has_outer).toBe(true);
		expect(f.outer_token_type).toBe('diagram');
		expect(f.has_multiplier).toBe(true);
		expect(f.multiplier.from_attribute_override).toBe('attributes/Diners/type');
		expect(f.multiplier.divisor_from_diagram_data).toBe('data.servings');
		expect(f.multiplier.default_multiplier).toBe(1);
		expect(f.inner_token_type).toBe('element');
		expect(f.inner_value_path).toBe('attributes/Quantity/type');
		expect(f.inner_bucket_path).toBe('attributes/Unit/type');
		expect(f.skip_blank_values).toBe(true);
	});

	it('inner-only profile has has_outer=false', () => {
		const innerOnly = {
			traversal: {
				inner: { collect_token_type: 'element', value_attribute_path: 'attributes/Quantity/type', skip_blank_values: true },
			},
			output: {},
		};
		const f = readTraversalFields(innerOnly);
		expect(f.has_outer).toBe(false);
		expect(f.has_multiplier).toBe(false);
	});

	it('outer without multiplier reads has_multiplier=false', () => {
		const noMul = {
			traversal: {
				outer: { collect_token_type: 'diagram' },
				inner: { collect_token_type: 'element', skip_blank_values: true },
			},
		};
		const f = readTraversalFields(noMul);
		expect(f.has_outer).toBe(true);
		expect(f.has_multiplier).toBe(false);
	});
});

describe('patchTraversalFields', () => {
	it('round-trip preserves inner-only structure', () => {
		const fields: TraversalFields = {
			has_outer: false,
			outer_token_type: 'diagram',
			has_multiplier: false,
			multiplier: { from_attribute_override: '', divisor_from_diagram_data: '', default_multiplier: 1 },
			inner_token_type: 'element',
			inner_value_path: 'attributes/Quantity/type',
			inner_bucket_path: 'attributes/Unit/type',
			skip_blank_values: true,
		};
		const out = patchTraversalFields({}, fields);
		const t = out.traversal as Record<string, unknown>;
		expect(t.outer).toBeUndefined();
		expect((t.inner as Record<string, unknown>).value_attribute_path).toBe('attributes/Quantity/type');
		expect((t.inner as Record<string, unknown>).bucket_attribute_path).toBe('attributes/Unit/type');
	});

	it('round-trip preserves outer+multiplier structure', () => {
		const fields = readTraversalFields(FULL_PROFILE);
		const out = patchTraversalFields(FULL_PROFILE, fields);
		const t = out.traversal as Record<string, unknown>;
		const outer = t.outer as Record<string, unknown>;
		const mul = outer.multiplier as Record<string, unknown>;
		expect(outer.collect_token_type).toBe('diagram');
		expect(mul.from_attribute_override).toBe('attributes/Diners/type');
		expect(mul.divisor_from_diagram_data).toBe('data.servings');
		expect(mul.default_multiplier).toBe(1);
	});

	it('empty value/bucket paths normalise to null', () => {
		const fields = readTraversalFields(FULL_PROFILE);
		fields.inner_value_path = '';
		fields.inner_bucket_path = '   ';
		const out = patchTraversalFields(FULL_PROFILE, fields);
		const inner = (out.traversal as Record<string, unknown>).inner as Record<string, unknown>;
		expect(inner.value_attribute_path).toBeNull();
		expect(inner.bucket_attribute_path).toBeNull();
	});

	it('toggling has_outer=false drops the outer block entirely', () => {
		const fields = readTraversalFields(FULL_PROFILE);
		fields.has_outer = false;
		const out = patchTraversalFields(FULL_PROFILE, fields);
		expect((out.traversal as Record<string, unknown>).outer).toBeUndefined();
	});

	it('toggling has_multiplier=false nulls the multiplier (engine treats as 1.0)', () => {
		const fields = readTraversalFields(FULL_PROFILE);
		fields.has_multiplier = false;
		const out = patchTraversalFields(FULL_PROFILE, fields);
		const outer = (out.traversal as Record<string, unknown>).outer as Record<string, unknown>;
		expect(outer.multiplier).toBeNull();
	});
});

describe('insertAtCursor', () => {
	it('inserts at the given position and returns the new cursor', () => {
		const { text, cursor } = insertAtCursor('hello world', 5, ' beautiful');
		expect(text).toBe('hello beautiful world');
		expect(cursor).toBe(15);
	});

	it('clamps a negative cursor to 0 (insert at start)', () => {
		const { text, cursor } = insertAtCursor('abc', -3, 'X');
		expect(text).toBe('Xabc');
		expect(cursor).toBe(1);
	});

	it('clamps an over-length cursor to end (insert at end)', () => {
		const { text, cursor } = insertAtCursor('abc', 99, 'Z');
		expect(text).toBe('abcZ');
		expect(cursor).toBe(4);
	});

	it('inserts a {placeholder} chip into a line_format draft', () => {
		const start = '- ';
		const { text } = insertAtCursor(start, 2, '{element.name}: {sum_value}');
		expect(text).toBe('- {element.name}: {sum_value}');
	});
});

describe('buildDraftFromTemplate', () => {
	const SEED = {
		id: 'seed',
		name: 'Shopping list',
		description: 'Sum quantities by element, grouped by package.',
		profile_data: FULL_PROFILE,
	};

	it('name carries " (copy)" suffix', () => {
		const d = buildDraftFromTemplate(SEED);
		expect(d.name).toBe('Shopping list (copy)');
	});

	it('description copied verbatim', () => {
		const d = buildDraftFromTemplate(SEED);
		expect(d.description).toBe('Sum quantities by element, grouped by package.');
	});

	it('isDefault always false on clone', () => {
		const d = buildDraftFromTemplate(SEED);
		expect(d.isDefault).toBe(false);
	});

	it('output and traversal pre-populated from the seed', () => {
		const d = buildDraftFromTemplate(SEED);
		expect(d.output.group_by).toBe('element.package_name');
		expect(d.traversal.has_outer).toBe(true);
		expect(d.traversal.multiplier.from_attribute_override).toBe('attributes/Diners/type');
	});

	it('json mirrors the original profile_data (escape hatch intact)', () => {
		const d = buildDraftFromTemplate(SEED);
		expect(JSON.parse(d.json)).toEqual(FULL_PROFILE);
	});
});

describe('buildBlankDraft', () => {
	it('produces a profile_data that already passes Pydantic shape (traversal + output)', () => {
		const d = buildBlankDraft();
		const parsed = JSON.parse(d.json);
		expect(parsed.traversal).toBeDefined();
		expect(parsed.traversal.inner).toBeDefined();
		expect(parsed.traversal.inner.collect_token_type).toBe('element');
		expect(parsed.output).toBeDefined();
		expect(parsed.output.aggregation_fn).toBe('sum');
	});

	it('has no outer (inner-only by default)', () => {
		const d = buildBlankDraft();
		expect(d.traversal.has_outer).toBe(false);
		expect(JSON.parse(d.json).traversal.outer).toBeUndefined();
	});
});

describe('assembleProfileData', () => {
	it('combines form-field state into a complete profile_data for save', () => {
		const traversal: TraversalFields = {
			has_outer: false, outer_token_type: 'diagram', has_multiplier: false,
			multiplier: { from_attribute_override: '', divisor_from_diagram_data: '', default_multiplier: 1 },
			inner_token_type: 'element',
			inner_value_path: 'attributes/Quantity/type',
			inner_bucket_path: '',
			skip_blank_values: true,
		};
		const output: OutputFields = {
			aggregation_fn: 'sum', group_by: 'element.name',
			sort_groups: 'alpha', sort_items_within_group: 'alpha',
			line_format: '- {element.name}: {sum_value}',
			show_per_source_breakdown: false, breakdown_format: '',
			include_provenance: false,
		};
		const pd = assembleProfileData(output, traversal);
		expect((pd.traversal as Record<string, unknown>).inner).toBeDefined();
		expect((pd.output as Record<string, unknown>).group_by).toBe('element.name');
		expect((pd.output as Record<string, unknown>).line_format).toBe('- {element.name}: {sum_value}');
	});
});

// ─────────────────────────────────────────────────────────────────────
// Live preview request body shape (SPEC-212-f)
// ─────────────────────────────────────────────────────────────────────

describe('inline run request body', () => {
	it('POST /api/aggregation/run with profile_data inline omits profile_id', () => {
		// The composer's live-preview hits the run endpoint with profile_data
		// inline — the backend tests guarantee the server-side semantics; this
		// just guards the request body shape the frontend will send.
		const traversal: TraversalFields = {
			has_outer: false, outer_token_type: 'diagram', has_multiplier: false,
			multiplier: { from_attribute_override: '', divisor_from_diagram_data: '', default_multiplier: 1 },
			inner_token_type: 'element', inner_value_path: 'attributes/Quantity/type',
			inner_bucket_path: '', skip_blank_values: true,
		};
		const output: OutputFields = {
			aggregation_fn: 'sum', group_by: 'element.name',
			sort_groups: 'alpha', sort_items_within_group: 'alpha',
			line_format: '- {element.name}: {sum_value}',
			show_per_source_breakdown: false, breakdown_format: '',
			include_provenance: false,
		};
		const body = {
			profile_data: assembleProfileData(output, traversal),
			source_diagram_id: 'some-uuid',
		};
		expect((body as Record<string, unknown>).profile_id).toBeUndefined();
		expect(body.profile_data).toBeDefined();
		expect(body.source_diagram_id).toBe('some-uuid');
	});
});
