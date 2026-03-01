import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Edge label editing tests (WP-3).
 * Verifies EdgeLabel component exists and edge components import it.
 */

describe('EdgeLabel component', () => {
	const edgeLabelPath = resolve(__dirname, '../../src/lib/canvas/edges/EdgeLabel.svelte');
	const edgeLabelSrc = readFileSync(edgeLabelPath, 'utf-8');

	it('uses FlowEdgeLabel from @xyflow/svelte', () => {
		expect(edgeLabelSrc).toContain('EdgeLabel as FlowEdgeLabel');
		expect(edgeLabelSrc).toContain('<FlowEdgeLabel');
	});

	it('supports inline editing via double-click', () => {
		expect(edgeLabelSrc).toContain('ondblclick');
		expect(edgeLabelSrc).toContain('isEditing');
	});

	it('sanitizes input with DOMPurify', () => {
		expect(edgeLabelSrc).toContain('DOMPurify.sanitize');
	});

	it('dispatches edgelabeledit custom event on commit', () => {
		expect(edgeLabelSrc).toContain("'edgelabeledit'");
		expect(edgeLabelSrc).toContain('CustomEvent');
	});

	it('handles Enter to commit and Escape to cancel', () => {
		expect(edgeLabelSrc).toContain("event.key === 'Enter'");
		expect(edgeLabelSrc).toContain("event.key === 'Escape'");
	});
});

describe('Edge components use EdgeLabel', () => {
	const edgeDir = resolve(__dirname, '../../src/lib/canvas/edges');
	const edgeFiles = ['UsesEdge', 'DependsOnEdge', 'ComposesEdge', 'ImplementsEdge', 'ContainsEdge'];

	for (const name of edgeFiles) {
		it(`${name} imports EdgeLabel`, () => {
			const src = readFileSync(resolve(edgeDir, `${name}.svelte`), 'utf-8');
			expect(src).toContain("import EdgeLabel from './EdgeLabel.svelte'");
		});

		it(`${name} uses EdgeLabel component`, () => {
			const src = readFileSync(resolve(edgeDir, `${name}.svelte`), 'utf-8');
			expect(src).toContain('<EdgeLabel');
		});

		it(`${name} does not use textPath for labels`, () => {
			const src = readFileSync(resolve(edgeDir, `${name}.svelte`), 'utf-8');
			expect(src).not.toContain('<textPath');
		});
	}
});
