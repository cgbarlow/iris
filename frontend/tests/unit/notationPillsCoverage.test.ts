// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves them at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Issue #27 root cause: NotationPills hard-coded a 5-entry list and
 * silently dropped notations the rest of the system supports. The
 * regression that surfaced was BPMN — registered in the registry,
 * rendered by canvas, valid in the AI seed, present in the
 * NOTATION_TYPE_FALLBACK map in DiagramDialog — but missing from the
 * picker, so users had no way to choose it.
 *
 * This test asserts that every notation key present in
 * DiagramDialog.NOTATION_TYPE_FALLBACK is also present in
 * NotationPills.ALL_NOTATIONS, which keeps the picker honest if
 * someone adds an eighth notation later.
 *
 * Static-parser style — no runtime mount required.
 */

const PILLS = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/components/NotationPills.svelte'),
	'utf-8',
);
const DIALOG = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/components/DiagramDialog.svelte'),
	'utf-8',
);

function pillKeys(): string[] {
	const m = PILLS.match(/ALL_NOTATIONS\s*=\s*\[([\s\S]*?)\]/);
	if (!m) throw new Error('ALL_NOTATIONS array not found in NotationPills.svelte');
	const body = m[1];
	const keys: string[] = [];
	const re = /key:\s*'([^']+)'/g;
	let match: RegExpExecArray | null;
	while ((match = re.exec(body)) !== null) keys.push(match[1]);
	return keys;
}

function fallbackKeys(): string[] {
	const m = DIALOG.match(/NOTATION_TYPE_FALLBACK[^=]*=\s*\{([\s\S]*?)\n\t\};/);
	if (!m) throw new Error('NOTATION_TYPE_FALLBACK map not found in DiagramDialog.svelte');
	const body = m[1];
	const keys: string[] = [];
	const re = /^\s{2,}([a-z][a-z0-9_]*):/gm;
	let match: RegExpExecArray | null;
	while ((match = re.exec(body)) !== null) keys.push(match[1]);
	return keys;
}

describe('NotationPills coverage (issue #27)', () => {
	it('lists BPMN', () => {
		expect(pillKeys()).toContain('bpmn');
	});

	it('lists Markdown (so Text views are creatable)', () => {
		expect(pillKeys()).toContain('markdown');
	});

	it('covers every key registered in NOTATION_TYPE_FALLBACK', () => {
		const pills = pillKeys();
		const fallback = fallbackKeys();
		expect(fallback.length).toBeGreaterThan(0);
		const missing = fallback.filter((k) => !pills.includes(k));
		expect(missing).toEqual([]);
	});

	it('exposes a `notations` filter prop so callers can scope (e.g. EntityDialog excludes markdown)', () => {
		expect(PILLS).toMatch(/notations\?:\s*string\[\]/);
		const ENTITY_DIALOG = readFileSync(
			resolve(import.meta.dirname, '../../src/lib/canvas/controls/EntityDialog.svelte'),
			'utf-8',
		);
		// EntityDialog must restrict the picker — text views have no entities.
		expect(ENTITY_DIALOG).toMatch(/notations=\{\[[^\]]*\]\}/);
		expect(ENTITY_DIALOG).not.toMatch(/notations=\{\[[^\]]*'markdown'/);
	});
});
