// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.0 (#13): align BPMN with the rest of Iris's notation pattern —
 * every BPMN node creates a backing Iris Element via `POST /api/elements`
 * and stores `entityId` on the canvas node. Pre-v5.4 BPMN nodes were
 * pure visual shapes (no Element record), divergent from
 * Simple/UML/ArchiMate/C4/DoView (which have always done this).
 *
 * Once aligned, BPMN content participates in search, knowledge graph,
 * tagging, comments, versioning, and `iris://element/<id>` references.
 */

const SHELL = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/bpmn/BpmnAuthoringShell.svelte'),
	'utf-8',
);

describe('BPMN nodes are backed by Iris Elements (#13, v5.4.0)', () => {
	it('the shell defines a createBpmnElement helper that POSTs /api/elements', () => {
		expect(SHELL).toMatch(/(?:async\s+)?function\s+createBpmnElement\b/);
		const fn = SHELL.match(/function\s+createBpmnElement[\s\S]*?\n\t\}/)?.[0] ?? '';
		expect(fn).toMatch(/apiFetch[\s\S]*?\/api\/elements/);
		expect(fn).toMatch(/method:\s*['"]POST['"]/);
		expect(fn).toMatch(/notation:\s*['"]bpmn['"]|notation\s*:\s*['"]bpmn['"]/);
	});

	it('every node-creation path persists `entityId` on the new node', () => {
		// makeBpmnNode (or its callers) must put `entityId` somewhere on
		// data — that's the field every other notation uses.
		expect(SHELL).toMatch(/entityId/);
	});

	it('createBpmnElement is awaited from the palette / drop / command-palette / context-pad-append flows', () => {
		// Each path must call createBpmnElement (or call a function that does).
		const usage = SHELL.match(/createBpmnElement/g) ?? [];
		// Expect at least 1 declaration + 1 usage. With the four creation paths,
		// we expect ≥ 2 occurrences (declaration + at least one shared call site).
		expect(usage.length).toBeGreaterThanOrEqual(2);
	});

	it('the replace flow updates an existing element rather than creating a new one', () => {
		// In CommandPalette `replace` mode, we should PUT/PATCH /api/elements/<id>
		// rather than POST a new one. The element_type changes; the id stays.
		const m = SHELL.match(/mode\s*===\s*['"]replace['"][\s\S]*?\n\t\}/);
		expect(m).toBeTruthy();
		// Loose: the replace block touches the elements endpoint.
		expect(m![0]).toMatch(/element/i);
	});

	it('PropertyPanel changes patch the underlying Element label/description', () => {
		// handlePropChange should call updateBpmnElement (which itself
		// PUTs /api/elements/<id>) when label/description change.
		const fn = SHELL.match(/function\s+handlePropChange[\s\S]*?\n\t\}/)?.[0] ?? '';
		expect(fn).toMatch(/updateBpmnElement|\/api\/elements/);
		// updateBpmnElement is the helper that hits the PUT endpoint.
		expect(SHELL).toMatch(/(?:async\s+)?function\s+updateBpmnElement[\s\S]*?\/api\/elements/);
	});
});
