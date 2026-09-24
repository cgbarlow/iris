import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Canvas node description sync tests (WP-5).
 * Verifies that the model detail page refreshes node descriptions
 * from linked entities after canvas load.
 *
 * ADR-248 (v6.50.1): the elements now arrive in one
 * `GET /api/diagrams/{id}/elements` call (see
 * diagramElementHydration.test.ts for the hydration logic itself).
 */

describe('Node description sync', () => {
	const pageSrc = readFileSync(
		resolve(__dirname, '../../src/routes/views/[id]/+page.svelte'),
		'utf-8',
	);
	const helperSrc = readFileSync(
		resolve(__dirname, '../../src/lib/canvas/diagramElementHydration.ts'),
		'utf-8',
	);

	it('defines refreshNodeDescriptions over the batched elements', () => {
		expect(pageSrc).toContain('function refreshNodeDescriptions(elements: Element[])');
	});

	it('refreshes node descriptions after parseCanvasData in loadDiagram', () => {
		// Verify the call order: parseCanvasData() then the elements load
		// that drives refreshNodeDescriptions().
		const loadBody = pageSrc.slice(pageSrc.indexOf('async function loadDiagram('));
		const parseIndex = loadBody.indexOf('parseCanvasData()');
		const refreshIndex = loadBody.indexOf('loadDiagramElements(id)');
		expect(parseIndex).toBeGreaterThan(-1);
		expect(refreshIndex).toBeGreaterThan(parseIndex);
		expect(pageSrc).toContain('refreshNodeDescriptions(elements)');
	});

	it('hydrates nodes with entityId via elementToNodeData', () => {
		expect(helperSrc).toContain('node.data?.entityId');
		// ADR-192 (issue #164): label + description (and all other
		// renderer-visible fields) flow through the shared
		// elementToNodeData() helper.
		expect(helperSrc).toContain('elementToNodeData(element)');
		expect(helperSrc).toMatch(/hydrated\.(label|description)/);
	});
});
