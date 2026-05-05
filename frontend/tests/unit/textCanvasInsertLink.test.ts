// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves them at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Issue #27 — bug C: the toolbar Add Element / Link Element / Add
 * Diagram buttons were creating canvas nodes regardless of the
 * canvas mode. In Text mode the user expects an `iris://` markdown
 * link inserted at the cursor instead. UAT: "When I did Add Diagram
 * and Add Element I did not see these show up as links in the canvas."
 */

const TEXT_CANVAS = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/text/TextCanvas.svelte'),
	'utf-8',
);
const PAGE = readFileSync(
	resolve(import.meta.dirname, '../../src/routes/views/[id]/+page.svelte'),
	'utf-8',
);

describe('Text view link insertion (issue #27)', () => {
	it('TextCanvas exposes the textarea ref via $bindable so the parent can splice text in', () => {
		expect(TEXT_CANVAS).toMatch(/textareaEl[\s\S]*\$bindable\(\)/);
		expect(TEXT_CANVAS).toMatch(/bind:this=\{textareaEl\}/);
	});

	it('parent page binds the textarea and provides insertMarkdownAtCursor', () => {
		expect(PAGE).toMatch(/bind:textareaEl=\{textTextareaEl\}/);
		expect(PAGE).toMatch(/function insertMarkdownAtCursor\(/);
	});

	it('handleAddElement inserts an iris://element/<id> markdown link in text mode', () => {
		const m = PAGE.match(/async function handleAddElement\([\s\S]*?\n\t\}/);
		expect(m).toBeTruthy();
		const block = m![0];
		expect(block).toMatch(/canvasType\s*===\s*'text'/);
		expect(block).toMatch(/insertMarkdownAtCursor\([^)]*iris:\/\/element\//);
	});

	it('handleLinkElement inserts an iris://element/<id> markdown link in text mode', () => {
		const m = PAGE.match(/function handleLinkElement\([\s\S]*?\n\t\}/);
		expect(m).toBeTruthy();
		const block = m![0];
		expect(block).toMatch(/canvasType\s*===\s*'text'/);
		expect(block).toMatch(/insertMarkdownAtCursor\([^)]*iris:\/\/element\//);
	});

	it('handleInsertDiagram inserts an iris://diagram/<id> markdown link in text mode', () => {
		const m = PAGE.match(/function handleInsertDiagram\([\s\S]*?\n\t\}/);
		expect(m).toBeTruthy();
		const block = m![0];
		expect(block).toMatch(/canvasType\s*===\s*'text'/);
		expect(block).toMatch(/insertMarkdownAtCursor\([^)]*iris:\/\/diagram\//);
	});
});
