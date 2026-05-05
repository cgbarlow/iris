// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves them at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Issue #32: in v5.1.1 the `{:else if canvasType === 'text'}` branch
 * existed only inside the `{#if editing}` block, so browse mode for a
 * Text view fell through to `{:else if canvasNodes.length === 0}` and
 * showed "Start Building". The browse-mode branch is now in place
 * before the empty-canvas check.
 */
const SRC = readFileSync(
	resolve(import.meta.dirname, '../../src/routes/views/[id]/+page.svelte'),
	'utf-8',
);

describe('Text view browse-mode rendering (issue #32)', () => {
	it('the browse-mode `canvas-area` chain has a Text branch', () => {
		// Find the chain: {#if editing} … {/if} {:else if canvasType === 'text'} … {:else if canvasNodes.length === 0}
		// The order matters — the Text check must come before the empty-canvas check.
		const idxText = SRC.indexOf("{:else if canvasType === 'text'}");
		const idxEmpty = SRC.indexOf('{:else if canvasNodes.length === 0}');
		expect(idxText).toBeGreaterThan(-1);
		expect(idxEmpty).toBeGreaterThan(-1);

		// At least one Text branch must occur before the empty-canvas check
		// (the editor-only branch is also covered by the existing v5.1.1 chain).
		const textBranchesBefore = (SRC.slice(0, idxEmpty).match(/\{:else if canvasType === 'text'\}/g) ?? []).length;
		expect(textBranchesBefore).toBeGreaterThanOrEqual(2);
	});

	it('renders TextCanvas with editing=false in browse mode', () => {
		// The browse-mode branch must mount TextCanvas with editing={false}.
		expect(SRC).toMatch(/<TextCanvas\b[\s\S]*editing=\{false\}/);
	});

	it('shows a "This text view is empty" prompt when content is blank (mirrors canvas Start Building)', () => {
		expect(SRC).toMatch(/This text view is empty/);
		expect(SRC).toMatch(/Start Writing/);
	});
});
