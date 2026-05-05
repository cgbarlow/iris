// @ts-nocheck
/**
 * @vitest-environment jsdom
 *
 * Issue #32 reopen — markdown editing was a plain textarea. v5.3.0
 * adds a toolbar with selection-wrap helpers (Bold / Italic / H1-H3 /
 * UL / OL / Quote / Code / Link / Image / HR). Tests target the pure
 * helpers exported from `markdownEditorToolbarHelpers.ts` so the
 * Svelte component stays a thin wrapper.
 */
import { describe, it, expect } from 'vitest';
import {
	wrapSelection,
	prefixLines,
	insertAtCursor,
	type EditorOp,
} from '$lib/canvas/text/markdownEditorToolbarHelpers';

function ta(value: string, selStart: number, selEnd = selStart) {
	const el = document.createElement('textarea');
	el.value = value;
	el.selectionStart = selStart;
	el.selectionEnd = selEnd;
	return el;
}

describe('wrapSelection — bold / italic / inline code / link', () => {
	it('wraps the selection with `**` for bold', () => {
		const el = ta('hello world', 0, 5);
		const op: EditorOp = wrapSelection(el, '**', '**');
		expect(op.value).toBe('**hello** world');
		expect(op.selectionStart).toBe(2);
		expect(op.selectionEnd).toBe(7);
	});

	it('wraps the selection with `*` for italic', () => {
		const el = ta('greetings', 0, 9);
		const op = wrapSelection(el, '*', '*');
		expect(op.value).toBe('*greetings*');
	});

	it('wraps with `` ` `` for inline code', () => {
		const el = ta('foo', 0, 3);
		const op = wrapSelection(el, '`', '`');
		expect(op.value).toBe('`foo`');
	});

	it('inserts empty markers at cursor when there is no selection', () => {
		const el = ta('|', 1, 1);
		const op = wrapSelection(el, '**', '**');
		expect(op.value).toBe('|****');
		// Caret should sit between the two markers so the user can type.
		expect(op.selectionStart).toBe(3);
		expect(op.selectionEnd).toBe(3);
	});
});

describe('prefixLines — headings / lists / quote', () => {
	it('prepends `# ` for H1 on the current line', () => {
		const el = ta('hello\nworld', 0, 0);
		const op = prefixLines(el, '# ');
		expect(op.value).toBe('# hello\nworld');
	});

	it('prepends `## ` for H2 even when caret is mid-line', () => {
		const el = ta('hello world', 6, 6);
		const op = prefixLines(el, '## ');
		expect(op.value).toBe('## hello world');
	});

	it('prepends `- ` for UL on every selected line', () => {
		const el = ta('a\nb\nc', 0, 5);
		const op = prefixLines(el, '- ');
		expect(op.value).toBe('- a\n- b\n- c');
	});

	it('prepends `1. ` for OL — each line gets the same `1.` prefix (markdown auto-numbers)', () => {
		const el = ta('a\nb\nc', 0, 5);
		const op = prefixLines(el, '1. ');
		expect(op.value).toBe('1. a\n1. b\n1. c');
	});

	it('prepends `> ` for blockquote', () => {
		const el = ta('quote me', 0, 0);
		const op = prefixLines(el, '> ');
		expect(op.value).toBe('> quote me');
	});

	it('toggles off the prefix if the line already has it', () => {
		// Click H2 again on a line that already starts with `## ` → strip it.
		const el = ta('## already heading', 0, 0);
		const op = prefixLines(el, '## ');
		expect(op.value).toBe('already heading');
	});
});

describe('insertAtCursor — Link / Image / HR snippets', () => {
	it('inserts a markdown link template with caret at the URL position', () => {
		const el = ta('see ', 4, 4);
		const op = insertAtCursor(el, '[](url)');
		expect(op.value).toBe('see [](url)');
	});

	it('wraps a non-empty selection in a link template', () => {
		const el = ta('see Iris docs', 4, 13);
		const op = wrapSelection(el, '[', '](url)');
		expect(op.value).toBe('see [Iris docs](url)');
	});

	it('inserts an image template', () => {
		const el = ta('', 0, 0);
		const op = insertAtCursor(el, '![alt](path)');
		expect(op.value).toBe('![alt](path)');
	});

	it('inserts a horizontal rule on its own line', () => {
		const el = ta('above\n', 6, 6);
		const op = insertAtCursor(el, '\n---\n');
		expect(op.value).toBe('above\n\n---\n');
	});
});
