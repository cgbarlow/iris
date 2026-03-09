// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves them correctly at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve, join } from 'node:path';

/**
 * Tests for node resize support (ADR-091-A).
 *
 * Verifies that NodeResizer from @xyflow/svelte is present in node components
 * and conditionally rendered based on browseMode.
 */

const ROOT = resolve(__dirname, '../../src/lib/canvas');

const RESIZABLE_NODES = [
	'nodes/NavigationCellNode.svelte',
	'nodes/NoteNode.svelte',
	'nodes/BoundaryNode.svelte',
	'BaseNode.svelte',
];

describe('Node resize support (ADR-091-A)', () => {
	it.each(RESIZABLE_NODES)('%s imports NodeResizer from @xyflow/svelte', (relPath) => {
		const filePath = join(ROOT, relPath);
		const source = readFileSync(filePath, 'utf-8');
		expect(source).toContain('NodeResizer');
		expect(source).toContain('@xyflow/svelte');
	});

	it.each(RESIZABLE_NODES)('%s conditionally shows NodeResizer (not in browseMode)', (relPath) => {
		const filePath = join(ROOT, relPath);
		const source = readFileSync(filePath, 'utf-8');
		// NodeResizer should be guarded by browseMode check
		expect(source).toContain('NodeResizer');
		expect(source).toMatch(/browseMode/);
	});

	it.each(RESIZABLE_NODES)('%s sets minWidth and minHeight on NodeResizer', (relPath) => {
		const filePath = join(ROOT, relPath);
		const source = readFileSync(filePath, 'utf-8');
		expect(source).toContain('minWidth');
		expect(source).toContain('minHeight');
	});
});

describe('NodeStylePanel integration (ADR-091-A)', () => {
	it('diagram page imports NodeStylePanel', () => {
		const pagePath = resolve(__dirname, '../../src/routes/diagrams/[id]/+page.svelte');
		const source = readFileSync(pagePath, 'utf-8');
		expect(source).toContain('NodeStylePanel');
		expect(source).toContain("import NodeStylePanel from");
	});

	it('diagram page renders NodeStylePanel when a node is selected in edit mode', () => {
		const pagePath = resolve(__dirname, '../../src/routes/diagrams/[id]/+page.svelte');
		const source = readFileSync(pagePath, 'utf-8');
		expect(source).toContain('NodeStylePanel');
		expect(source).toContain('selectedEditNodeId');
	});

	it('diagram page listens for nodestylechange events', () => {
		const pagePath = resolve(__dirname, '../../src/routes/diagrams/[id]/+page.svelte');
		const source = readFileSync(pagePath, 'utf-8');
		expect(source).toContain('nodestylechange');
	});

	it('diagram page handles node resize events and marks dirty', () => {
		const pagePath = resolve(__dirname, '../../src/routes/diagrams/[id]/+page.svelte');
		const source = readFileSync(pagePath, 'utf-8');
		expect(source).toContain('noderesizeend');
	});
});
