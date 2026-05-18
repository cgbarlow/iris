import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Template viewer — deleted source element (v6.8.6, ADR-197, issue #173 item 2).
 *
 * Bug: the template detail page's "(source element deleted)" fallback was
 * wired to `tpl.source_element_id` — but the id stays populated after the
 * source is soft-deleted (FK has no ON DELETE clause), so the conditional
 * never fell through to the deleted branch. The dangling link 404'd.
 *
 * Fix: the conditional checks `tpl.source_element_name` (which the
 * backend correctly nulls via subquery when the source is soft-deleted —
 * see backend fix in app/element_templates/service.py same PR). The
 * label no longer falls back to printing the raw id.
 *
 * Static-parser style.
 */

const src = readFileSync(
	resolve(__dirname, '../../src/routes/element-templates/[id]/+page.svelte'),
	'utf-8',
);

describe('Template viewer — deleted-source conditional', () => {
	it('uses source_element_name as the existence signal, not source_element_id', () => {
		expect(src).toMatch(/\{#if\s+tpl\.source_element_name\}/);
	});

	it('no longer keys the {#if} on source_element_id (the dangling FK)', () => {
		expect(src).not.toMatch(/\{#if\s+tpl\.source_element_id\}/);
	});

	it('still renders an anchor to /elements/{source_element_id} when source is present', () => {
		// The href continues to use the id — only the conditional changed.
		expect(src).toContain('href="/elements/{tpl.source_element_id}"');
	});

	it('shows "(source element deleted)" copy in the else branch', () => {
		expect(src).toContain('(source element deleted)');
	});

	it('drops the "?? tpl.source_element_id" label fallback (no raw id rendered)', () => {
		// When source_element_name is truthy, render it directly. The
		// previous "?? tpl.source_element_id" fallback was the visible
		// symptom of the bug — a link with a UUID as its label.
		expect(src).not.toContain('tpl.source_element_name ?? tpl.source_element_id');
	});
});
