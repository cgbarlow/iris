// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.1 — issue #46 items #6 + #7: The BPMN Problems panel must cap
 * itself at a fixed height AND scroll its own contents. The v5.4.0 fix
 * only added overflow-y: auto; flex-shrink: 0 is missing, so the flex
 * algorithm collapses the max-height: 200px constraint and the panel
 * pushes the page off-screen.
 */

const SRC = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/bpmn/BpmnAuthoringShell.svelte'),
	'utf-8',
);

describe('Problems panel layout (v5.4.1, issue #46 items #6 + #7)', () => {
	it('.bpmn-shell__problems has max-height, overflow-y: auto, and flex-shrink: 0', () => {
		// Match the .bpmn-shell__problems CSS rule body.
		const ruleMatch = SRC.match(/\.bpmn-shell__problems\s*\{([^}]*)\}/);
		expect(ruleMatch, '.bpmn-shell__problems rule').not.toBeNull();
		const body = ruleMatch![1];

		expect(body).toMatch(/max-height\s*:\s*200px/);
		expect(body).toMatch(/overflow-y\s*:\s*auto/);
		expect(body).toMatch(/flex-shrink\s*:\s*0/);
	});
});
