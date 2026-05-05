// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves them at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Issue #32 reopen — `showTocDrawer` was wired but no button toggled
 * it, so the TOC never appeared. v5.3.0 adds a TOC button on the
 * canvas toolbar that fires when `canvasType === 'text'`.
 */

const PAGE = readFileSync(
	resolve(import.meta.dirname, '../../src/routes/views/[id]/+page.svelte'),
	'utf-8',
);

describe('Text view TOC toggle (issue #32 reopen)', () => {
	it('the page has a TOC button rendered for Text views', () => {
		// The button must appear conditionally on canvasType === 'text' so it
		// doesn't show on canvas/sequence/BPMN views. Match the literal label
		// "TOC" inside a button for Text canvases.
		expect(PAGE).toMatch(/canvasType\s*===\s*'text'[\s\S]{0,800}<button[\s\S]*?TOC[\s\S]*?<\/button>/);
	});

	it('the button toggles showTocDrawer (the existing v5.1.0 state)', () => {
		expect(PAGE).toMatch(/showTocDrawer\s*=\s*!\s*showTocDrawer|showTocDrawer\s*=\s*true/);
	});
});
