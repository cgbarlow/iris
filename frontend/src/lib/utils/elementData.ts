/**
 * Helpers for the element page's read-only **Data** panel (ADR-243, issue #292).
 *
 * An element's `data` blob is free-form: MCP `create_element(s)` and
 * element templates can write any keys, and the collection export carries
 * them verbatim. The element page only special-cases a UML `attributes`
 * array (the Attributes accordion), so every other key used to be stored,
 * exported, and invisible. `extraDataEntries` turns the remaining keys
 * into display rows so nothing in `data` is hidden from the person who
 * owns the element.
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

/** A whole-value http(s) URL — the only strings rendered as links.
 *  Anchored so `javascript:` or prose that merely contains a URL never links. */
const HTTP_URL = /^https?:\/\/\S+$/i;

/** Rows for every `data` key not rendered elsewhere on the element page,
 *  in authored (insertion) order. */
export function extraDataEntries(data: unknown): ElementDataEntry[] {
	if (data === null || typeof data !== 'object' || Array.isArray(data)) return [];
	const entries: ElementDataEntry[] = [];
	for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
		// Only an array is shown by the Attributes accordion; any other
		// `attributes` value would otherwise be invisible.
		if (key === 'attributes' && Array.isArray(value)) continue;
		if (value !== null && typeof value === 'object') {
			entries.push({ key, kind: 'json', value: JSON.stringify(value, null, 2) });
		} else if (typeof value === 'string' && HTTP_URL.test(value)) {
			entries.push({ key, kind: 'text', value, href: value });
		} else {
			entries.push({ key, kind: 'text', value: String(value) });
		}
	}
	return entries;
}
