// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.1 — issue #46 item #4: When clipboard image paste fails, the
 * user used to see absolutely nothing because the catch swallowed
 * everything silently. Surface the error via console.error so it shows
 * in dev tools (and via an optional callback for the parent).
 */

const SRC = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/text/TextCanvas.svelte'),
	'utf-8',
);

describe('TextCanvas paste-error surfacing (v5.4.1, issue #46 item #4)', () => {
	it('the catch block in handlePaste calls console.error with the failure', () => {
		// Locate handlePaste and its catch block.
		const handlePasteMatch = SRC.match(/async function handlePaste[\s\S]*?\n\s*\}\n/);
		expect(handlePasteMatch, 'handlePaste found').not.toBeNull();
		const fn = handlePasteMatch![0];

		// Locate the catch block.
		const catchMatch = fn.match(/catch\s*\(([^)]*)\)\s*\{[\s\S]*?\}/);
		expect(catchMatch, 'catch block in handlePaste').not.toBeNull();
		const catchBody = catchMatch![0];

		// The catch must call console.error (with whatever arguments) — i.e.
		// it is no longer a silent no-op.
		expect(catchBody).toMatch(/console\.error\s*\(/);
	});
});
