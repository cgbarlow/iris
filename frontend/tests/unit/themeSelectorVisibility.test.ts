// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * v5.4.0 — ThemeSelector is irrelevant on BPMN (theme is fixed by the
 * BPMN-default theme seeded in m043) and on Text views (no canvas to
 * theme). Hide it for those two notations.
 */

const PAGE = readFileSync(
	resolve(import.meta.dirname, '../../src/routes/views/[id]/+page.svelte'),
	'utf-8',
);

describe('ThemeSelector visibility (issue cluster, v5.4.0)', () => {
	it('every <ThemeSelector> mount is gated on a non-bpmn / non-text guard', () => {
		// Find every {#if …}…<ThemeSelector …/> with comments allowed in between.
		const matches = PAGE.matchAll(/\{#if[^}]+\}[\s\S]{0,400}?<ThemeSelector\b/g);
		const guards = [...matches].map((m) => m[0]);
		expect(guards.length).toBeGreaterThan(0);
		for (const guard of guards) {
			// Allow optional `as string` cast (svelte-check needs it because
			// NotationType doesn't include 'markdown'/'bpmn' yet).
			expect(guard).toMatch(/notation\s*(?:as\s+\w+\s*)?\)?\s*!==?\s*['"]bpmn['"]/);
			expect(guard).toMatch(/(?:canvasType|notation)\s*(?:as\s+\w+\s*)?\)?\s*!==?\s*['"](?:text|markdown)['"]/);
		}
	});
});
