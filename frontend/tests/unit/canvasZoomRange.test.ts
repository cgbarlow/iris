// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { CANVAS_MIN_ZOOM } from '$lib/canvas/zoom';

/**
 * ADR-253 — canvases zoom out far enough to see a large diagram whole.
 * Svelte Flow's default minZoom (0.5) also caps fitView, so a 274-node
 * family tree opened at 50% with most of it off screen.
 */

const CANVASES = ['UnifiedCanvas', 'FullViewCanvas', 'ModelCanvas', 'BrowseCanvas'];

function source(name: string): string {
	return readFileSync(resolve(import.meta.dirname, `../../src/lib/canvas/${name}.svelte`), 'utf-8');
}

describe('Canvas minimum zoom (ADR-253)', () => {
	it('is well below the Svelte Flow default of 0.5', () => {
		expect(CANVAS_MIN_ZOOM).toBeGreaterThan(0);
		expect(CANVAS_MIN_ZOOM).toBeLessThanOrEqual(0.05);
	});

	for (const name of CANVASES) {
		it(`${name} passes minZoom to every <SvelteFlow>`, () => {
			const src = source(name);
			const flows = src.match(/^\t*<SvelteFlow\n[\s\S]*?\n\t*>/gm) ?? [];
			expect(flows.length).toBeGreaterThan(0);
			for (const flow of flows) {
				expect(flow).toMatch(/minZoom=\{CANVAS_MIN_ZOOM\}/);
			}
			expect(src).toMatch(/import \{ CANVAS_MIN_ZOOM \} from '\$lib\/canvas\/zoom'/);
		});
	}
});
