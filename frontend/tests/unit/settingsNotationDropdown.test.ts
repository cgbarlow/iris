/**
 * v5.16.0 (ADR-161, SPEC-161-A): the Default Notation dropdown on
 * /settings must list every notation ID registered in the backend
 * (simple, uml, archimate, c4, doview, markdown, bpmn). v5.15.x
 * shipped with only the first 4; the missing 3 (doview, markdown,
 * bpmn) made the user preference inconsistent with what's authorable.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const PAGE = resolve(__dirname, '../../src/routes/settings/+page.svelte');

describe('Default Notation dropdown', () => {
	const source = readFileSync(PAGE, 'utf-8');

	it.each([
		['simple'],
		['uml'],
		['archimate'],
		['c4'],
		['doview'],
		['markdown'],
		['bpmn'],
	])('lists "%s" as an <option> value', (notationId) => {
		expect(source).toContain(`<option value="${notationId}">`);
	});

	it('has all 7 notation options inside settings-notation select', () => {
		const selectStart = source.indexOf('id="settings-notation"');
		const selectEnd = source.indexOf('</select>', selectStart);
		const block = source.slice(selectStart, selectEnd);
		const matches = block.match(/<option value="[^"]+"/g) ?? [];
		expect(matches).toHaveLength(7);
	});
});
