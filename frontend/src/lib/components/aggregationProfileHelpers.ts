/**
 * SPEC-212-f: helpers for the form-based aggregation profile editor.
 *
 * Pure functions that lift fields out of (and patch them back into)
 * the ProfileData JSON shape. Co-located with AggregationProfileEditor.svelte
 * + LineFormatComposer + TraversalBuilder + AggregationTemplateGallery so
 * a single round-trip representation is shared across all three (DRY §13).
 *
 * Enum literals (TokenType, SortMode, AggregationFn) intentionally mirror
 * the backend Pydantic definitions in backend/app/aggregation/models.py.
 * The backend validates on save — the frontend uses these only to
 * populate dropdowns. If a new value is added backend-side, add it here
 * (and the tests will catch any drift between the two).
 */

export type TokenType = 'element' | 'diagram' | 'package' | 'set' | 'collection';
export type SortMode = 'alpha' | 'none';
export type AggregationFn = 'sum' | 'count';

export const TOKEN_TYPES: readonly TokenType[] = [
	'element', 'diagram', 'package', 'set', 'collection',
] as const;
export const SORT_MODES: readonly SortMode[] = ['alpha', 'none'] as const;
export const AGGREGATION_FNS: readonly AggregationFn[] = ['sum', 'count'] as const;

/** All `{placeholder}` tokens the engine substitutes in `line_format`
 *  (see backend/app/aggregation/engine.py `_render_line`). The composer
 *  surfaces these as clickable chips. */
export const LINE_FORMAT_PLACEHOLDERS = [
	{ key: 'element.name', label: '{element.name}', hint: 'The element\'s display name' },
	{ key: 'element.id', label: '{element.id}', hint: 'The element\'s UUID (link target)' },
	{ key: 'sum_value', label: '{sum_value}', hint: 'Aggregated value (sum or count)' },
	{ key: 'bucket', label: '{bucket}', hint: 'Bucket value (e.g. units), unspaced' },
	{ key: 'bucket_spaced', label: '{bucket_spaced}', hint: 'Bucket with a leading space when set' },
] as const;

export const BREAKDOWN_PLACEHOLDERS = [
	{ key: 'sources_joined', label: '{sources_joined}', hint: 'Per-source values joined by commas' },
] as const;

/** Fields lifted from `output.*` into form widgets. */
export interface OutputFields {
	aggregation_fn: AggregationFn;
	group_by: string;
	sort_groups: SortMode;
	sort_items_within_group: SortMode;
	line_format: string;
	show_per_source_breakdown: boolean;
	breakdown_format: string;
	include_provenance: boolean;
}

const DEFAULT_OUTPUT: OutputFields = {
	aggregation_fn: 'sum',
	group_by: '',
	sort_groups: 'alpha',
	sort_items_within_group: 'alpha',
	line_format: '- {element.name}: {sum_value}{bucket_spaced}',
	show_per_source_breakdown: false,
	breakdown_format: ' ({sources_joined})',
	include_provenance: false,
};

function getObj(parent: Record<string, unknown>, key: string): Record<string, unknown> {
	const v = parent[key];
	return v && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : {};
}

function pickStr(obj: Record<string, unknown>, key: string, fallback: string): string {
	const v = obj[key];
	return typeof v === 'string' ? v : fallback;
}

function pickEnum<T extends string>(obj: Record<string, unknown>, key: string, allowed: readonly T[], fallback: T): T {
	const v = obj[key];
	return typeof v === 'string' && (allowed as readonly string[]).includes(v) ? (v as T) : fallback;
}

function pickBool(obj: Record<string, unknown>, key: string, fallback: boolean): boolean {
	const v = obj[key];
	return typeof v === 'boolean' ? v : fallback;
}

/** Read every output field from a profile_data object, falling back to
 *  per-field defaults that match backend OutputConfig defaults. */
export function readOutputFields(profileData: Record<string, unknown> | null | undefined): OutputFields {
	const output = profileData ? getObj(profileData, 'output') : {};
	return {
		aggregation_fn: pickEnum(output, 'aggregation_fn', AGGREGATION_FNS, DEFAULT_OUTPUT.aggregation_fn),
		group_by: pickStr(output, 'group_by', DEFAULT_OUTPUT.group_by),
		sort_groups: pickEnum(output, 'sort_groups', SORT_MODES, DEFAULT_OUTPUT.sort_groups),
		sort_items_within_group: pickEnum(output, 'sort_items_within_group', SORT_MODES, DEFAULT_OUTPUT.sort_items_within_group),
		line_format: pickStr(output, 'line_format', DEFAULT_OUTPUT.line_format),
		show_per_source_breakdown: pickBool(output, 'show_per_source_breakdown', DEFAULT_OUTPUT.show_per_source_breakdown),
		breakdown_format: pickStr(output, 'breakdown_format', DEFAULT_OUTPUT.breakdown_format),
		include_provenance: pickBool(output, 'include_provenance', DEFAULT_OUTPUT.include_provenance),
	};
}

/** Merge form-field values back into a profile_data object, returning
 *  a NEW object (does not mutate the input). `group_by` empty-string
 *  is normalised to `null` so the engine treats it as ungrouped. */
export function patchOutputFields(
	profileData: Record<string, unknown> | null | undefined,
	fields: OutputFields,
): Record<string, unknown> {
	const base: Record<string, unknown> = profileData ? { ...profileData } : {};
	const output = profileData ? getObj(profileData, 'output') : {};
	base.output = {
		...output,
		aggregation_fn: fields.aggregation_fn,
		group_by: fields.group_by.trim() === '' ? null : fields.group_by.trim(),
		sort_groups: fields.sort_groups,
		sort_items_within_group: fields.sort_items_within_group,
		line_format: fields.line_format,
		show_per_source_breakdown: fields.show_per_source_breakdown,
		breakdown_format: fields.breakdown_format,
		include_provenance: fields.include_provenance,
	};
	return base;
}

/** Fields lifted from `traversal.*` into the wizard. */
export interface MultiplierFields {
	from_attribute_override: string;
	divisor_from_diagram_data: string;
	default_multiplier: number;
}

export interface TraversalFields {
	has_outer: boolean;
	outer_token_type: TokenType;
	has_multiplier: boolean;
	multiplier: MultiplierFields;
	inner_token_type: TokenType;
	inner_value_path: string;
	inner_bucket_path: string;
	skip_blank_values: boolean;
}

const DEFAULT_TRAVERSAL: TraversalFields = {
	has_outer: false,
	outer_token_type: 'diagram',
	has_multiplier: false,
	multiplier: {
		from_attribute_override: '',
		divisor_from_diagram_data: '',
		default_multiplier: 1,
	},
	inner_token_type: 'element',
	inner_value_path: '',
	inner_bucket_path: '',
	skip_blank_values: true,
};

export function readTraversalFields(profileData: Record<string, unknown> | null | undefined): TraversalFields {
	const traversal = profileData ? getObj(profileData, 'traversal') : {};
	const outerRaw = traversal['outer'];
	const hasOuter = outerRaw !== null && outerRaw !== undefined && typeof outerRaw === 'object';
	const outer = hasOuter ? (outerRaw as Record<string, unknown>) : {};
	const multiplierRaw = outer['multiplier'];
	const hasMultiplier = multiplierRaw !== null && multiplierRaw !== undefined && typeof multiplierRaw === 'object';
	const multiplier = hasMultiplier ? (multiplierRaw as Record<string, unknown>) : {};
	const inner = getObj(traversal, 'inner');
	return {
		has_outer: hasOuter,
		outer_token_type: pickEnum(outer, 'collect_token_type', TOKEN_TYPES, DEFAULT_TRAVERSAL.outer_token_type),
		has_multiplier: hasMultiplier,
		multiplier: {
			from_attribute_override: pickStr(multiplier, 'from_attribute_override', ''),
			divisor_from_diagram_data: pickStr(multiplier, 'divisor_from_diagram_data', ''),
			default_multiplier: typeof multiplier['default_multiplier'] === 'number'
				? (multiplier['default_multiplier'] as number)
				: DEFAULT_TRAVERSAL.multiplier.default_multiplier,
		},
		inner_token_type: pickEnum(inner, 'collect_token_type', TOKEN_TYPES, DEFAULT_TRAVERSAL.inner_token_type),
		inner_value_path: pickStr(inner, 'value_attribute_path', ''),
		inner_bucket_path: pickStr(inner, 'bucket_attribute_path', ''),
		skip_blank_values: pickBool(inner, 'skip_blank_values', DEFAULT_TRAVERSAL.skip_blank_values),
	};
}

export function patchTraversalFields(
	profileData: Record<string, unknown> | null | undefined,
	fields: TraversalFields,
): Record<string, unknown> {
	const base: Record<string, unknown> = profileData ? { ...profileData } : {};
	const inner: Record<string, unknown> = {
		collect_token_type: fields.inner_token_type,
		value_attribute_path: fields.inner_value_path.trim() === '' ? null : fields.inner_value_path.trim(),
		bucket_attribute_path: fields.inner_bucket_path.trim() === '' ? null : fields.inner_bucket_path.trim(),
		skip_blank_values: fields.skip_blank_values,
	};
	const traversal: Record<string, unknown> = { inner };
	if (fields.has_outer) {
		const outer: Record<string, unknown> = {
			collect_token_type: fields.outer_token_type,
		};
		if (fields.has_multiplier) {
			outer.multiplier = {
				from_attribute_override: fields.multiplier.from_attribute_override.trim() === ''
					? null
					: fields.multiplier.from_attribute_override.trim(),
				divisor_from_diagram_data: fields.multiplier.divisor_from_diagram_data.trim() === ''
					? null
					: fields.multiplier.divisor_from_diagram_data.trim(),
				default_multiplier: fields.multiplier.default_multiplier,
			};
		} else {
			outer.multiplier = null;
		}
		traversal.outer = outer;
	}
	base.traversal = traversal;
	return base;
}

/** Insert a placeholder at a cursor position in a text field. Returns
 *  the new text and the new cursor position (after the inserted token). */
export function insertAtCursor(
	text: string,
	cursor: number,
	insertion: string,
): { text: string; cursor: number } {
	const safe = Math.max(0, Math.min(cursor, text.length));
	const next = text.slice(0, safe) + insertion + text.slice(safe);
	return { text: next, cursor: safe + insertion.length };
}

/** Build a draft from a seeded template profile (Option E gallery path).
 *  The seeded profile_data populates form fields; the user only sees JSON
 *  if they click "Advanced". */
export interface SeededProfile {
	id: string;
	name: string;
	description: string | null;
	profile_data: Record<string, unknown>;
}

export interface FormDraft {
	name: string;
	description: string;
	json: string;
	isDefault: boolean;
	output: OutputFields;
	traversal: TraversalFields;
}

export function buildDraftFromTemplate(source: SeededProfile): FormDraft {
	return {
		name: `${source.name} (copy)`,
		description: source.description ?? '',
		json: JSON.stringify(source.profile_data, null, 2),
		isDefault: false,
		output: readOutputFields(source.profile_data),
		traversal: readTraversalFields(source.profile_data),
	};
}

/** Build a blank draft (Option E "Blank" card). Defaults match the backend
 *  Pydantic defaults so a save with no edits produces a valid profile. */
export function buildBlankDraft(): FormDraft {
	const traversal: TraversalFields = {
		...DEFAULT_TRAVERSAL,
		multiplier: { ...DEFAULT_TRAVERSAL.multiplier },
	};
	const output: OutputFields = { ...DEFAULT_OUTPUT };
	const profileData = patchOutputFields(patchTraversalFields({}, traversal), output);
	return {
		name: '',
		description: '',
		json: JSON.stringify(profileData, null, 2),
		isDefault: false,
		output,
		traversal,
	};
}

/** Reassemble a full profile_data object from form-field state. Used at
 *  save time to merge the form back into JSON the backend will accept. */
export function assembleProfileData(
	output: OutputFields,
	traversal: TraversalFields,
): Record<string, unknown> {
	return patchOutputFields(patchTraversalFields({}, traversal), output);
}
