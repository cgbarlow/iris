// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves them at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Issue #33: EntityDialog had no `case 'bpmn':` in its entity-type switch
 * so BPMN views silently fell through to `default:` (Simple). Users on a
 * BPMN canvas saw Actor / Boundary / Component / Note / Service / etc.
 * instead of the BPMN catalogue.
 *
 * Coverage rule: every notation key visible in the picker
 * (NotationPills.ALL_NOTATIONS) must have a matching `case '<key>':`
 * branch in EntityDialog (markdown excepted — text views have no
 * entities to add).
 */
const PILLS = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/components/NotationPills.svelte'),
	'utf-8',
);
const DIALOG = readFileSync(
	resolve(import.meta.dirname, '../../src/lib/canvas/controls/EntityDialog.svelte'),
	'utf-8',
);

function pillKeys(): string[] {
	const m = PILLS.match(/ALL_NOTATIONS\s*=\s*\[([\s\S]*?)\]/);
	if (!m) throw new Error('ALL_NOTATIONS array not found in NotationPills.svelte');
	const keys: string[] = [];
	const re = /key:\s*'([^']+)'/g;
	let match: RegExpExecArray | null;
	while ((match = re.exec(m[1])) !== null) keys.push(match[1]);
	return keys;
}

function dialogCaseKeys(): string[] {
	const keys: string[] = [];
	const re = /case\s+'([a-z][a-z0-9_]*)':/g;
	let match: RegExpExecArray | null;
	while ((match = re.exec(DIALOG)) !== null) keys.push(match[1]);
	return keys;
}

describe('EntityDialog notation coverage (issue #33)', () => {
	it('has a case for BPMN', () => {
		expect(dialogCaseKeys()).toContain('bpmn');
	});

	it('imports BPMN_ENTITY_TYPES + BPMN_DIAGRAM_TYPE_FILTER', () => {
		expect(DIALOG).toMatch(/BPMN_ENTITY_TYPES/);
		expect(DIALOG).toMatch(/BPMN_DIAGRAM_TYPE_FILTER/);
	});

	it('the BPMN branch reads the BPMN catalogue, not the Simple fallback', () => {
		const block = DIALOG.match(/case 'bpmn':[\s\S]*?break;/)?.[0];
		expect(block).toBeTruthy();
		expect(block).toMatch(/BPMN_ENTITY_TYPES/);
		expect(block).not.toMatch(/SIMPLE_ENTITY_TYPES/);
	});

	it('every user-pickable notation has a corresponding switch case (markdown excluded — text views have no entities)', () => {
		const cases = dialogCaseKeys();
		const expected = pillKeys().filter((k) => k !== 'markdown' && k !== 'simple');
		// `simple` is the `default:` fallback by design; it's not listed as an explicit case.
		const missing = expected.filter((k) => !cases.includes(k));
		expect(missing).toEqual([]);
	});
});
