// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves them at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.2.0 (issue #37): mount the six BPMN authoring surfaces specified
 * in ADR-136 §UX into the canvas. Pre-v5.2.0 they existed as files on
 * disk but were never imported anywhere; net effect was that BPMN was
 * catalogue-only.
 *
 * This test is the regression guard — if a future change removes any
 * of the six mounts, or breaks the connection guard / drag-drop
 * wiring, the test should catch it. Static-parser style (matches
 * `notationPillsCoverage.test.ts` etc).
 */

const ROOT = resolve(import.meta.dirname, '../..');
const SHELL = resolve(ROOT, 'src/lib/canvas/bpmn/BpmnAuthoringShell.svelte');
const TOAST = resolve(ROOT, 'src/lib/canvas/bpmn/BpmnToast.svelte');
const PAGE = resolve(ROOT, 'src/routes/views/[id]/+page.svelte');
const UNIFIED = resolve(ROOT, 'src/lib/canvas/UnifiedCanvas.svelte');
const RENDERER = resolve(ROOT, 'src/lib/canvas/renderers/BpmnRenderer.svelte');

describe('BPMN authoring shell exists (issue #37, v5.2.0)', () => {
	it('the shell + toast files exist', () => {
		expect(existsSync(SHELL)).toBe(true);
		expect(existsSync(TOAST)).toBe(true);
	});

	it('the views detail page imports + mounts the shell behind a notation/editing guard', () => {
		const src = readFileSync(PAGE, 'utf-8');
		expect(src).toMatch(/import\s+BpmnAuthoringShell\s+from\s+['"]\$lib\/canvas\/bpmn\/BpmnAuthoringShell\.svelte['"]/);
		expect(src).toMatch(/<BpmnAuthoringShell\b/);
		// The mount must be guarded by notation === 'bpmn' so non-BPMN views
		// keep the existing canvas branch unchanged. Accept either {#if … }
		// or {:else if … } since the chain is part of an existing if/else.
		// v5.4.0 (#8) inserts a trio toolbar between the guard and the shell;
		// loosen the lookahead window from 400 to 4000 chars.
		const mountBlock = src.match(/\{(?:#if|:else if)[^}]*notation\s*===\s*'bpmn'[\s\S]{0,4000}<BpmnAuthoringShell/);
		expect(mountBlock).toBeTruthy();
	});
});

describe('BpmnAuthoringShell mounts the BPMN UX surfaces', () => {
	const src = existsSync(SHELL) ? readFileSync(SHELL, 'utf-8') : '';

	it('imports the surface components the shell mounts directly + the toast', () => {
		// ContextPad is intentionally NOT imported by the shell — it mounts
		// inside BpmnRenderer (covered in the separate describe block below)
		// and receives its action handler via setContext.
		expect(src).toMatch(/import\s+BpmnPalette\b/);
		expect(src).toMatch(/import\s+CommandPalette\b/);
		expect(src).toMatch(/import\s+EventMatrixPicker\b/);
		expect(src).toMatch(/import\s+PropertyPanel\b/);
		expect(src).toMatch(/import\s+ProblemsPanel\b/);
		expect(src).toMatch(/import\s+BpmnToast\b/);
	});

	it('mounts each surface', () => {
		expect(src).toMatch(/<BpmnPalette\b/);
		expect(src).toMatch(/<CommandPalette\b/);
		expect(src).toMatch(/<EventMatrixPicker\b/);
		expect(src).toMatch(/<PropertyPanel\b/);
		expect(src).toMatch(/<ProblemsPanel\b/);
		expect(src).toMatch(/<BpmnToast\b/);
	});

	it('binds the N / A / R hotkeys at the shell level (not via CommandPalette\'s self-binding)', () => {
		// CommandPalette must be told NOT to self-bind, otherwise the hotkeys would
		// also fire on non-BPMN views (CommandPalette is a global keydown listener).
		expect(src).toMatch(/bindShortcuts=\{false\}/);
		// Shell-level handler must check the keys and avoid hijacking inputs/textareas.
		expect(src).toMatch(/'n'|'N'/);
		expect(src).toMatch(/'a'|'A'/);
		expect(src).toMatch(/'r'|'R'/);
		expect(src).toMatch(/INPUT|TEXTAREA|isContentEditable/);
	});

	it('wires canConnect into UnifiedCanvas\'s onbeforeconnect', () => {
		expect(src).toMatch(/import\s*\{[^}]*canConnect[^}]*\}\s*from/);
		expect(src).toMatch(/onbeforeconnect=/);
	});

	it('wires the palette drop handler into UnifiedCanvas\'s ondropentity', () => {
		expect(src).toMatch(/ondropentity=/);
	});

	it('wires the ContextPad action handler into UnifiedCanvas\'s oncontextpadaction', () => {
		expect(src).toMatch(/oncontextpadaction=/);
	});
});

describe('UnifiedCanvas exposes the BPMN integration hooks', () => {
	const src = readFileSync(UNIFIED, 'utf-8');

	it('declares onbeforeconnect / ondropentity / oncontextpadaction props', () => {
		expect(src).toMatch(/onbeforeconnect\?:/);
		expect(src).toMatch(/ondropentity\?:/);
		expect(src).toMatch(/oncontextpadaction\?:/);
	});

	it('passes onbeforeconnect to <SvelteFlow isValidConnection={…}>', () => {
		expect(src).toMatch(/isValidConnection=/);
	});

	it('forwards the palette drag-drop through CanvasDropArea (v5.3.1: hook moved out of UnifiedCanvas script)', () => {
		expect(src).toMatch(/import\s+CanvasDropArea\b/);
		expect(src).toMatch(/<CanvasDropArea\b[\s\S]*?ondropentity=/);
		// CanvasDropArea must be a child of SvelteFlowProvider so its
		// useSvelteFlow() call lands inside the provider.
		const slice = src.match(/<SvelteFlowProvider[\s\S]*?<CanvasDropArea/);
		expect(slice).toBeTruthy();
	});

	it('CanvasDropArea handles the palette MIME and calls useSvelteFlow inside SvelteFlowProvider', () => {
		const drop = readFileSync(
			resolve(ROOT, 'src/lib/canvas/CanvasDropArea.svelte'),
			'utf-8',
		);
		expect(drop).toMatch(/useSvelteFlow/);
		expect(drop).toMatch(/application\/iris-bpmn-entity/);
		expect(drop).toMatch(/screenToFlowPosition/);
	});

	it('shares the ContextPad action handler via setContext so BpmnRenderer can call it', () => {
		expect(src).toMatch(/setContext\(['"]bpmnContextPadAction['"]/);
	});

	it('UnifiedCanvas does NOT call useSvelteFlow at script level (v5.3.1 regression guard)', () => {
		// useSvelteFlow at script level executes before the
		// SvelteFlowProvider in the same component's template — that's
		// the v5.2.0 bug that broke every canvas (issue #37 reopen).
		expect(src).not.toMatch(/^\s*const\s+\w+\s*=\s*useSvelteFlow/m);
		expect(src).not.toMatch(/import[\s\S]*?useSvelteFlow[\s\S]*?from\s+['"]@xyflow\/svelte['"]/);
	});
});

describe('BpmnRenderer mounts ContextPad when selected', () => {
	const src = readFileSync(RENDERER, 'utf-8');

	it('imports ContextPad', () => {
		expect(src).toMatch(/import\s+ContextPad\s+from/);
	});

	it('declares an id prop (xyflow auto-passes node id to custom renderers)', () => {
		expect(src).toMatch(/id\?:\s*string/);
	});

	it('mounts ContextPad with the node id when selected', () => {
		expect(src).toMatch(/<ContextPad\b[\s\S]*?nodeId=\{id\}[\s\S]*?\/>/);
	});

	it('reads the action handler from the bpmnContextPadAction context', () => {
		expect(src).toMatch(/getContext\b/);
		expect(src).toMatch(/['"]bpmnContextPadAction['"]/);
	});
});
