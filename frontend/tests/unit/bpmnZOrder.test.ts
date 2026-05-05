// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.0 (#3): when items stack (e.g. lane on pool), the user needs a
 * way to bring forward / send backward. Adds two ContextPad actions
 * (bring_forward, send_backward) and shell handlers that mutate the
 * node's `zIndex`.
 */

const PAD = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/palette/ContextPad.svelte'),
	'utf-8',
);
const SHELL = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/bpmn/BpmnAuthoringShell.svelte'),
	'utf-8',
);

describe('Z-order ContextPad actions (#3, v5.4.0)', () => {
	it('ContextPad declares bring_forward + send_backward actions', () => {
		expect(PAD).toMatch(/bring_forward/);
		expect(PAD).toMatch(/send_backward/);
	});

	it('the action union/type accepts the two new ids', () => {
		expect(PAD).toMatch(/'bring_forward'/);
		expect(PAD).toMatch(/'send_backward'/);
	});
});

describe('Z-order shell handler (#3, v5.4.0)', () => {
	it('handleContextPadAction has cases for the two new actions', () => {
		const fn = SHELL.match(/function handleContextPadAction[\s\S]*?\n\t\}/)?.[0] ?? '';
		expect(fn).toMatch(/case\s+'bring_forward'/);
		expect(fn).toMatch(/case\s+'send_backward'/);
	});

	it('the handler mutates a `zIndex` field on the canvas node', () => {
		expect(SHELL).toMatch(/zIndex/);
	});
});
