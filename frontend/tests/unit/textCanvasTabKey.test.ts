// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves them at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Issue #31: Tab in the markdown editor used to move focus (browser
 * default for textareas). It now indents at the cursor instead, with
 * Esc-then-Tab as the keyboard escape hatch (preserves WCAG 2.1.2 No
 * Keyboard Trap).
 */
const SRC = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/text/TextCanvas.svelte'),
	'utf-8',
);

describe('TextCanvas Tab key handling (issue #31)', () => {
	it('declares a keydown handler', () => {
		expect(SRC).toMatch(/function handleKeydown\(/);
		expect(SRC).toMatch(/onkeydown=\{handleKeydown\}/);
	});

	it('intercepts Tab to insert a literal \\t at the selection', () => {
		// Either an explicit `=== 'Tab'` check or a guard `!== 'Tab'` returning early.
		expect(SRC).toMatch(/e\.key (?:===|!==) 'Tab'/);
		expect(SRC).toMatch(/preventDefault\(\)/);
		// Tab insert: the insertion expression splices '\t' into the value at selection
		expect(SRC).toMatch(/\+ '\\t' \+/);
		expect(SRC).toMatch(/setSelectionRange/);
	});

	it('handles Shift+Tab as outdent', () => {
		expect(SRC).toMatch(/e\.shiftKey/);
	});

	it('keeps an Esc-then-Tab escape hatch (WCAG 2.1.2 No Keyboard Trap)', () => {
		expect(SRC).toMatch(/e\.key === 'Escape'/);
		expect(SRC).toMatch(/tabTrapEnabled/);
	});

	it('forwards the change so the parent dirty flag flips', () => {
		// commitChange must call oncontentchange so the page-level canvasDirty wiring fires.
		expect(SRC).toMatch(/function commitChange\(/);
		expect(SRC).toMatch(/commitChange\(ta\)/);
		const commitBlock = SRC.match(/function commitChange[\s\S]*?oncontentchange\?\.\([^)]*\);/);
		expect(commitBlock).toBeTruthy();
	});
});
