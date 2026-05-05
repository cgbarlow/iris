// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves them at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Issue #27 — bug B (root cause): saveCanvas() was always writing
 * `data: { nodes, edges }` to the API. For a Text view that's an empty
 * pair of arrays, so the markdown source got blown away on every save.
 *
 * Bug A (root cause): `oncontentchange` updated `diagram.data.content`
 * but never set canvasDirty=true, so the Save button stayed greyed out.
 *
 * These two bugs together explain the UAT report: "After saving, in
 * the browse view of this I now see a normal canvas diagram with the
 * diagram and element boxes I added in the markdown editor, however
 * none of the markdown text I wrote."
 */

const PAGE = readFileSync(
	resolve(import.meta.dirname, '../../src/routes/views/[id]/+page.svelte'),
	'utf-8',
);

describe('Text view save persistence (issue #27)', () => {
	it('saveCanvas branches on canvasType === "text" before building the request body', () => {
		// The branch must precede the apiFetch PUT so the body sees the right `data`.
		const m = PAGE.match(/function saveCanvas\(\)[\s\S]*?await apiFetch/);
		expect(m).toBeTruthy();
		const block = m![0];
		expect(block).toMatch(/canvasType\s*===\s*'text'/);
		expect(block).toMatch(/content:\s*markdownContent/);
	});

	it('non-text views still persist nodes and edges', () => {
		const m = PAGE.match(/function saveCanvas\(\)[\s\S]*?await apiFetch/);
		expect(m![0]).toMatch(/nodes:\s*canvasNodes,\s*edges:\s*canvasEdges/);
	});

	it('TextCanvas oncontentchange callback marks the page dirty', () => {
		// The wired callback at the TextCanvas instantiation site must set canvasDirty=true,
		// otherwise the Save button stays disabled when the user types in the markdown editor.
		const m = PAGE.match(/<TextCanvas[\s\S]*?\/>/);
		expect(m).toBeTruthy();
		const block = m![0];
		expect(block).toMatch(/oncontentchange=/);
		expect(block).toMatch(/canvasDirty\s*=\s*true/);
	});
});
