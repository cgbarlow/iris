/**
 * v5.3.0 (issue #32 reopen): pure helpers for the markdown editor
 * toolbar's selection-wrap operations. Kept separate from the Svelte
 * component so they're trivially unit-testable (matches the
 * `markdownHelpers.ts` pattern from ADR-137).
 *
 * Each helper returns a result object describing the new value + the
 * cursor position the parent should restore. Helpers do NOT mutate
 * the textarea directly (the caller does), so they're easy to test
 * with synthetic textarea elements.
 */

export interface EditorOp {
	value: string;
	selectionStart: number;
	selectionEnd: number;
}

/** Wrap the current selection (or insert empty markers at the cursor). */
export function wrapSelection(
	ta: HTMLTextAreaElement,
	prefix: string,
	suffix: string,
): EditorOp {
	const start = ta.selectionStart ?? 0;
	const end = ta.selectionEnd ?? start;
	const before = ta.value.slice(0, start);
	const sel = ta.value.slice(start, end);
	const after = ta.value.slice(end);
	const value = before + prefix + sel + suffix + after;
	if (sel.length === 0) {
		// Empty selection: place caret between the two markers so the
		// user can type the content directly.
		const caret = start + prefix.length;
		return { value, selectionStart: caret, selectionEnd: caret };
	}
	return {
		value,
		selectionStart: start + prefix.length,
		selectionEnd: end + prefix.length,
	};
}

/** Toggle a line-start prefix (e.g. `# `, `- `, `> `) on every line that
 *  the selection touches. If a line already starts with the prefix, the
 *  prefix is stripped (toggle behaviour matches GitHub / VSCode markdown
 *  shortcuts). When there's no selection, operates on the line containing
 *  the caret. */
export function prefixLines(ta: HTMLTextAreaElement, prefix: string): EditorOp {
	const start = ta.selectionStart ?? 0;
	const end = ta.selectionEnd ?? start;
	const value = ta.value;

	const lineStart = value.lastIndexOf('\n', Math.max(0, start - 1)) + 1;
	const lineEndRaw = value.indexOf('\n', end);
	const lineEnd = lineEndRaw === -1 ? value.length : lineEndRaw;

	const before = value.slice(0, lineStart);
	const middle = value.slice(lineStart, lineEnd);
	const after = value.slice(lineEnd);

	const lines = middle.split('\n');
	const allHavePrefix = lines.every((l) => l.startsWith(prefix));
	const transformed = allHavePrefix
		? lines.map((l) => l.slice(prefix.length))
		: lines.map((l) => prefix + l);
	const newMiddle = transformed.join('\n');
	const delta = newMiddle.length - middle.length;

	return {
		value: before + newMiddle + after,
		selectionStart: start + (allHavePrefix ? -prefix.length : prefix.length),
		selectionEnd: end + delta,
	};
}

/** Insert a literal snippet at the cursor (no wrapping). The caller can
 *  optionally include `\n` for block-level insertions like horizontal
 *  rules. */
export function insertAtCursor(ta: HTMLTextAreaElement, snippet: string): EditorOp {
	const start = ta.selectionStart ?? 0;
	const end = ta.selectionEnd ?? start;
	const value = ta.value.slice(0, start) + snippet + ta.value.slice(end);
	const caret = start + snippet.length;
	return { value, selectionStart: caret, selectionEnd: caret };
}

/** Apply an EditorOp back to the textarea. Convenience for the toolbar
 *  component. */
export function applyOp(ta: HTMLTextAreaElement, op: EditorOp) {
	ta.value = op.value;
	ta.setSelectionRange(op.selectionStart, op.selectionEnd);
	ta.focus();
}
