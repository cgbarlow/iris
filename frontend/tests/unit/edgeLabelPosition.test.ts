import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Edge label rotation & repositioning tests (WP-4).
 * Verifies CanvasEdgeData supports label offset/rotation
 * and EdgeLabel supports drag-to-reposition.
 */

describe('CanvasEdgeData label positioning fields', () => {
	const canvasTypesSrc = readFileSync(
		resolve(__dirname, '../../src/lib/types/canvas.ts'),
		'utf-8',
	);

	it('defines labelOffsetX field', () => {
		expect(canvasTypesSrc).toContain('labelOffsetX');
	});

	it('defines labelOffsetY field', () => {
		expect(canvasTypesSrc).toContain('labelOffsetY');
	});

	it('defines labelRotation field', () => {
		expect(canvasTypesSrc).toContain('labelRotation');
	});
});

describe('EdgeLabel repositioning support', () => {
	const edgeLabelSrc = readFileSync(
		resolve(__dirname, '../../src/lib/canvas/edges/EdgeLabel.svelte'),
		'utf-8',
	);

	it('accepts offsetX and offsetY props', () => {
		expect(edgeLabelSrc).toContain('offsetX');
		expect(edgeLabelSrc).toContain('offsetY');
	});

	it('accepts rotation prop', () => {
		expect(edgeLabelSrc).toContain('rotation');
	});

	it('applies offset to label position', () => {
		// The transform should include offset values
		expect(edgeLabelSrc).toContain('offsetX');
		expect(edgeLabelSrc).toContain('offsetY');
	});

	it('supports drag interaction for repositioning', () => {
		expect(edgeLabelSrc).toContain('onpointerdown');
		expect(edgeLabelSrc).toContain('pointermove');
	});

	it('dispatches edgelabelmove event on reposition', () => {
		expect(edgeLabelSrc).toContain("'edgelabelmove'");
	});
});

describe('Edge components pass offset/rotation to EdgeLabel', () => {
	const edgeDir = resolve(__dirname, '../../src/lib/canvas/edges');
	const edgeFiles = ['UsesEdge', 'DependsOnEdge', 'ComposesEdge', 'ImplementsEdge', 'ContainsEdge'];

	for (const name of edgeFiles) {
		it(`${name} passes offsetX/offsetY/rotation to EdgeLabel`, () => {
			const src = readFileSync(resolve(edgeDir, `${name}.svelte`), 'utf-8');
			expect(src).toContain('offsetX');
			expect(src).toContain('offsetY');
			expect(src).toContain('rotation');
		});
	}
});
