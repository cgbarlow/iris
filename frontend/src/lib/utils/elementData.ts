/**
 * Helpers for the element page's **Data** panel (ADR-243 read view,
 * ADR-245 edit mode; issue #292).
 *
 * An element's `data` blob is free-form: MCP `create_element(s)` and
 * element templates can write any keys, and the collection export carries
 * them verbatim. The element page only special-cases a UML `attributes`
 * array (the Attributes accordion), so every other key used to be stored,
 * exported, and invisible. `extraDataEntries` turns the remaining keys
 * into display rows; `toDataEditRows` / `applyDataEditRows` convert the
 * same keys to typed editor rows and back, validating on the way out.
 *
 * Values are returned as plain strings and rendered through Svelte's
 * escaping `{expressions}` — never `{@html}` (Protocol §7).
 */

export interface ElementDataEntry {
	key: string;
	/** `json` = pretty-printed nested object/array; `text` = scalar. */
	kind: 'text' | 'json';
	value: string;
	/** Set only for a whole-value http(s) URL string. */
	href?: string;
}

/** Editor value types. `json` covers objects, arrays, and `null`. */
export type DataValueType = 'text' | 'number' | 'boolean' | 'json';

export interface DataEditRow {
	key: string;
	type: DataValueType;
	/** Raw editor text; parsed according to `type` on save. */
	value: string;
}

export type ApplyDataEditResult =
	| { ok: true; data: Record<string, unknown> }
	| { ok: false; error: string };

/** A whole-value http(s) URL — the only strings rendered as links.
 *  Anchored so `javascript:` or prose that merely contains a URL never links. */
const HTTP_URL = /^https?:\/\/\S+$/i;

const ATTRIBUTES_KEY = 'attributes';

/** `data` entries the panel owns, in authored (insertion) order. Only an
 *  `attributes` array is excluded — that's what the Attributes accordion
 *  renders; any other `attributes` value would otherwise be invisible. */
function panelEntries(data: unknown): [string, unknown][] {
	if (data === null || typeof data !== 'object' || Array.isArray(data)) return [];
	return Object.entries(data as Record<string, unknown>).filter(
		([key, value]) => !(key === ATTRIBUTES_KEY && Array.isArray(value)),
	);
}

/** Read-mode rows for every `data` key not rendered elsewhere on the page. */
export function extraDataEntries(data: unknown): ElementDataEntry[] {
	return panelEntries(data).map(([key, value]) => {
		if (value !== null && typeof value === 'object') {
			return { key, kind: 'json', value: JSON.stringify(value, null, 2) };
		}
		if (typeof value === 'string' && HTTP_URL.test(value)) {
			return { key, kind: 'text', value, href: value };
		}
		return { key, kind: 'text', value: String(value) };
	});
}

/** Edit-mode rows for the same keys, typed so a save preserves each value's
 *  JSON type (a number stays a number, an object stays an object). */
export function toDataEditRows(data: unknown): DataEditRow[] {
	return panelEntries(data).map(([key, value]) => {
		switch (typeof value) {
			case 'string':
				return { key, type: 'text', value };
			case 'number':
				return { key, type: 'number', value: String(value) };
			case 'boolean':
				return { key, type: 'boolean', value: String(value) };
			default:
				return { key, type: 'json', value: JSON.stringify(value, null, 2) };
		}
	});
}

/** Parse editor rows back into `data` keys (excluding the `attributes`
 *  array, which the caller merges from the Attributes editor).
 *
 *  Fully blank rows are dropped; keys are trimmed; text values are kept
 *  verbatim. Returns the first validation error, if any. Set
 *  `attributesArrayInUse` when the Attributes table will write
 *  `data.attributes`, so a Data row can't silently collide with it. */
export function applyDataEditRows(
	rows: DataEditRow[],
	{ attributesArrayInUse }: { attributesArrayInUse: boolean },
): ApplyDataEditResult {
	const data: Record<string, unknown> = {};
	for (const [i, row] of rows.entries()) {
		const key = row.key.trim();
		if (!key) {
			if (!row.value.trim()) continue;
			return { ok: false, error: `Data row ${i + 1} needs a key` };
		}
		if (Object.hasOwn(data, key)) {
			return { ok: false, error: `Data key "${key}" is used more than once` };
		}
		if (key === ATTRIBUTES_KEY && attributesArrayInUse) {
			return { ok: false, error: `Data key "${key}" is reserved for the Attributes table` };
		}
		const raw = row.value.trim();
		switch (row.type) {
			case 'text':
				data[key] = row.value;
				break;
			case 'number': {
				const n = Number(raw);
				if (!raw || !Number.isFinite(n)) {
					return { ok: false, error: `Data "${key}" must be a number` };
				}
				data[key] = n;
				break;
			}
			case 'boolean':
				if (raw !== 'true' && raw !== 'false') {
					return { ok: false, error: `Data "${key}" must be true or false` };
				}
				data[key] = raw === 'true';
				break;
			case 'json':
				try {
					data[key] = JSON.parse(raw);
				} catch {
					return { ok: false, error: `Data "${key}" is not valid JSON` };
				}
				break;
		}
	}
	return { ok: true, data };
}
