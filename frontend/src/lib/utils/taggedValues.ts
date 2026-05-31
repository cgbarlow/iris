/**
 * Helpers for the Sparx EA `#NOTES#` tagged-value encoding (ADR-228).
 *
 * Sparx EA stores each tagged value's `value` field as a single
 * string, optionally followed by `#NOTES#` and a prescriptive
 * description block listing allowed values, the default, and a
 * human-readable description. Example:
 *
 *   "3#NOTES#Values: -,0,1,2,3,4,5\nDefault: -\nDescription: 0 - Does not exist\n1 - Initial …"
 *
 * `splitTaggedValue` separates the meaningful value from the notes so
 * the UI can edit each in its own control. `joinTaggedValue`
 * reassembles them. `isUnsetTaggedValue` mirrors the backend's
 * `_extract_tagged_value` (backend/app/diagrams/smart_markdown.py:139)
 * — `null`, `""`, `"-"`, and `"-#NOTES#…"` are all "unset".
 */

const NOTES_MARKER = '#NOTES#';

/** Split a Sparx tagged-value `value` string on the `#NOTES#` marker. */
export function splitTaggedValue(
	raw: string | null | undefined,
): { value: string; notes: string } {
	if (raw == null || raw === '' || raw === '-') {
		return { value: '', notes: '' };
	}
	const idx = raw.indexOf(NOTES_MARKER);
	if (idx < 0) return { value: raw, notes: '' };
	return {
		value: raw.slice(0, idx),
		notes: raw.slice(idx + NOTES_MARKER.length),
	};
}

/** Reassemble a tagged-value string from the editor's split form.
 *  Empty notes → omit the `#NOTES#` marker entirely. */
export function joinTaggedValue(value: string, notes: string): string {
	if (!notes) return value;
	return `${value}${NOTES_MARKER}${notes}`;
}

/** Match `_extract_tagged_value` in
 *  `backend/app/diagrams/smart_markdown.py:139` — treat `null`, `""`,
 *  `"-"`, and `"-#NOTES#…"` all as unset. */
export function isUnsetTaggedValue(
	raw: string | null | undefined,
): boolean {
	if (raw == null || raw === '' || raw === '-') return true;
	const { value } = splitTaggedValue(raw);
	return value === '' || value === '-';
}
