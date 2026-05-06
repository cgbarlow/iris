// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.1 — issue #46 item #11: Replace the 60-cell EventMatrixPicker
 * dialog with a compact ContextPad-style horizontal flyout that shows
 * ONLY the legal triggers for the chosen position. Reuses the
 * `isLegal` and `TRIGGERS` constants extracted to a shared
 * `bpmnEventModel.ts` module (DRY protocol #13).
 */

const EVENT_MODEL = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/palette/bpmnEventModel.ts'),
	'utf-8',
);

const FLYOUT = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/palette/EventTriggerFlyout.svelte'),
	'utf-8',
);

const SHELL = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/bpmn/BpmnAuthoringShell.svelte'),
	'utf-8',
);

describe('EventTriggerFlyout (v5.4.1, issue #46 item #11)', () => {
	it('bpmnEventModel exports TRIGGERS, isLegal, variantFor', () => {
		expect(EVENT_MODEL).toMatch(/export\s+const\s+TRIGGERS/);
		expect(EVENT_MODEL).toMatch(/export\s+function\s+isLegal/);
		expect(EVENT_MODEL).toMatch(/export\s+function\s+variantFor/);
	});

	it('EventTriggerFlyout filters by position via isLegal', () => {
		// Filters TRIGGERS using isLegal so only legal triggers render.
		expect(FLYOUT).toMatch(/isLegal/);
		expect(FLYOUT).toMatch(/TRIGGERS/);
		// Has open / position / onpick / onclose props.
		expect(FLYOUT).toMatch(/open\b/);
		expect(FLYOUT).toMatch(/position\b/);
		expect(FLYOUT).toMatch(/onpick\b/);
		expect(FLYOUT).toMatch(/onclose\b/);
	});

	it('BpmnAuthoringShell mounts EventTriggerFlyout and tracks pendingTriggerNodeId', () => {
		expect(SHELL).toMatch(/import\s+EventTriggerFlyout/);
		expect(SHELL).toMatch(/<EventTriggerFlyout\b/);
		expect(SHELL).toMatch(/pendingTriggerNodeId/);
	});
});
