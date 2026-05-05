// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves them at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Issue #32 reopen — Text views rendered markdown without heading
 * scale or list bullets because the User Guide layout
 * (`guide/+layout.svelte`) had typographic CSS rules scoped to
 * `.guide-content :global(…)` that the shared MarkdownView didn't.
 *
 * v5.3.0 lifts those rules into MarkdownView (the single source of
 * truth per protocol #13). This test asserts:
 *
 * 1. MarkdownView's <style> contains the heading-scale + list-bullet
 *    + image-border rules that USED to live in the guide layout.
 * 2. The guide layout no longer redeclares those same rules (so we
 *    don't have two truths in conflict).
 *
 * Static-parser style — matches the v5.1.x / v5.2 coverage tests.
 */

const MV = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/components/MarkdownView.svelte'),
	'utf-8',
);
const GL = readFileSync(
	resolve(import.meta.dirname, '../../src/routes/guide/+layout.svelte'),
	'utf-8',
);

describe('MarkdownView is the single source of truth for markdown typography (issue #32 reopen)', () => {
	it('MarkdownView styles h1 with a font-size larger than body text', () => {
		expect(MV).toMatch(/\.md-view\s*:global\(h1\)[\s\S]*?font-size/);
	});

	it('MarkdownView styles ul with list-style: disc', () => {
		expect(MV).toMatch(/\.md-view\s*:global\(ul\)[\s\S]*?list-style:\s*disc/);
	});

	it('MarkdownView styles ol with list-style: decimal', () => {
		expect(MV).toMatch(/\.md-view\s*:global\(ol\)[\s\S]*?list-style:\s*decimal/);
	});

	it('MarkdownView gives images a max-width and visible border', () => {
		expect(MV).toMatch(/\.md-view\s*:global\(img\)/);
		expect(MV).toMatch(/\.md-view\s*:global\(img\)[\s\S]*?max-width/);
	});

	it('MarkdownView styles strong with a heavier weight', () => {
		expect(MV).toMatch(/\.md-view\s*:global\(strong\)[\s\S]*?font-weight/);
	});

	it('the guide layout no longer redeclares heading / list / image rules', () => {
		// Layout-specific rules (sticky nav, grid) are fine; typography rules
		// must move to MarkdownView. Asserting on the rules the User Guide
		// previously owned (h1/h2/ul/ol/li/img/strong scoped to .guide-content).
		expect(GL).not.toMatch(/\.guide-content\s*:global\(h1\)/);
		expect(GL).not.toMatch(/\.guide-content\s*:global\(ul\)/);
		expect(GL).not.toMatch(/\.guide-content\s*:global\(img\)/);
	});
});
