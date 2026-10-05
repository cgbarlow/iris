// @ts-nocheck — sources are read as text; rendered sizes are checked in tests/e2e/canvas-text-readable.spec.ts.
/**
 * Issue #315 (ADR-260): canvas text must be readable. These guard the
 * style rules; the e2e spec checks what the browser actually renders.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, readdirSync } from 'node:fs';
import { resolve, join } from 'node:path';

const SRC = resolve(import.meta.dirname, '../../src');
const read = (rel: string) => readFileSync(join(SRC, rel), 'utf-8');

/** The declarations of the first rule whose selector is exactly `selector`. */
function rule(css: string, selector: string): string {
	const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
	const match = css.match(new RegExp(`(?:^|\\n)\\s*${escaped}\\s*\\{([^}]*)\\}`));
	if (!match) throw new Error(`no rule for ${selector}`);
	return match[1];
}

describe('node titles wrap instead of cutting off', () => {
	const label = rule(read('app.css'), '.canvas-node__label');

	it('does not force the title onto one line', () => {
		expect(label).not.toMatch(/white-space:\s*nowrap/);
	});

	it('clamps the title to three lines', () => {
		expect(label).toMatch(/-webkit-line-clamp:\s*3/);
		expect(label).toMatch(/overflow:\s*hidden/);
	});

	it('every title element carries the full name as a tooltip', () => {
		const dirs = ['lib/canvas', 'lib/canvas/nodes', 'lib/canvas/renderers'];
		const offenders: string[] = [];
		for (const dir of dirs) {
			for (const file of readdirSync(join(SRC, dir))) {
				if (!file.endsWith('.svelte')) continue;
				const src = read(join(dir, file));
				const labels = /<span class="(?:canvas|uml|archimate)-node__label"[^>]*>/g;
				for (const tag of src.match(labels) ?? []) {
					if (!tag.includes('title={data.label}')) offenders.push(`${dir}/${file}`);
				}
			}
		}
		expect(offenders).toEqual([]);
	});
});

describe('note text is readable at 100% zoom', () => {
	const note = read('lib/canvas/nodes/NoteNode.svelte');

	it('uses a 12px body, not the old 8px', () => {
		const body = rule(note, '.canvas-node--note');
		expect(body).toMatch(/font-size:\s*0\.75rem/);
		expect(note).not.toMatch(/font-size:\s*[89]px/);
	});

	it('sizes the header relative to the body so a theme font size scales both', () => {
		const header = rule(note, '.canvas-node--note :global(.canvas-node__header)');
		expect(header).toMatch(/font-size:\s*[\d.]+em/);
	});
});
