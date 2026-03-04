import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Canvas node description sync tests (WP-5).
 * Verifies that the model detail page refreshes node descriptions
 * from linked entities after canvas load.
 */

describe('Node description sync', () => {
	const pageSrc = readFileSync(
		resolve(__dirname, '../../src/routes/diagrams/[id]/+page.svelte'),
		'utf-8',
	);

	it('defines refreshNodeDescriptions function', () => {
		expect(pageSrc).toContain('async function refreshNodeDescriptions()');
	});

	it('calls refreshNodeDescriptions after parseCanvasData in loadModel', () => {
		// Verify the call order: parseCanvasData() then refreshNodeDescriptions()
		const parseIndex = pageSrc.indexOf('parseCanvasData()');
		const refreshIndex = pageSrc.indexOf('refreshNodeDescriptions()');
		expect(parseIndex).toBeGreaterThan(-1);
		expect(refreshIndex).toBeGreaterThan(-1);
		expect(refreshIndex).toBeGreaterThan(parseIndex);
	});

	it('fetches element data for nodes with entityId', () => {
		// The function should fetch element data for nodes with entityId
		expect(pageSrc).toContain("node.data?.entityId");
		// And update label and description
		expect(pageSrc).toContain('element.name');
		expect(pageSrc).toContain('element.description');
	});

	it('uses Promise.all for parallel entity fetching', () => {
		expect(pageSrc).toContain('Promise.all');
	});
});
