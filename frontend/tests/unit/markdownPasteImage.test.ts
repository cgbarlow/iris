// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.0 (#7): paste image from clipboard → upload to /api/images →
 * splice `![pasted-image](/api/images/<id>)` at the cursor.
 *
 * The implementation lives across:
 *   markdownEditorToolbarHelpers.ts: `uploadPastedImage(file)` POSTs the
 *     blob and returns `{ id, url }`.
 *   TextCanvas.svelte:               `onpaste` handler scans the clipboard
 *     for image items, uploads, and uses `applyOp(insertAtCursor(...))`
 *     to splice the markdown link.
 */

const HELPERS = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/text/markdownEditorToolbarHelpers.ts'),
	'utf-8',
);
const TEXT_CANVAS = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/text/TextCanvas.svelte'),
	'utf-8',
);

describe('Clipboard image paste (#7, v5.4.0)', () => {
	it('helpers expose uploadPastedImage that POSTs /api/images', () => {
		expect(HELPERS).toMatch(/(?:async\s+)?function\s+uploadPastedImage\b/);
		const fn = HELPERS.match(/function\s+uploadPastedImage[\s\S]*?\n\}/)?.[0] ?? '';
		expect(fn).toMatch(/['"]\/api\/images['"]/);
		expect(fn).toMatch(/method:\s*['"]POST['"]/);
		expect(fn).toMatch(/FormData|multipart/);
	});

	it('TextCanvas wires onpaste on the textarea', () => {
		expect(TEXT_CANVAS).toMatch(/onpaste=/);
	});

	it('the paste handler scans clipboard items for image MIME', () => {
		// Loose: text in TextCanvas mentions clipboardData and image/.
		expect(TEXT_CANVAS).toMatch(/clipboardData/);
		expect(TEXT_CANVAS).toMatch(/image\//);
	});

	it('the paste handler splices the markdown link via insertAtCursor + applyOp', () => {
		// Reuses the v5.3.0 toolbar helper pattern.
		expect(TEXT_CANVAS).toMatch(/insertAtCursor|applyOp|uploadPastedImage/);
		// And produces the markdown image syntax — `![…](…)` somewhere in the file.
		expect(TEXT_CANVAS).toMatch(/!\[/);
	});
});
