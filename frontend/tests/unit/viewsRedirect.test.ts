// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves them at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Issue #27: the user-facing "Diagrams" surface was renamed to
 * "Views" so a Text view sits naturally alongside a Canvas view. The
 * old `/diagrams` and `/diagrams/<id>` URLs still exist and 308-
 * redirect to `/views` so external bookmarks keep working.
 */

const ROOT = resolve(import.meta.dirname, '../../src/routes');

describe('Views rename redirects (issue #27)', () => {
	it('the new /views routes exist (renamed from /diagrams)', () => {
		expect(existsSync(resolve(ROOT, 'views/+page.svelte'))).toBe(true);
		expect(existsSync(resolve(ROOT, 'views/[id]/+page.svelte'))).toBe(true);
	});

	it('/diagrams issues a 308 redirect to /views preserving query + hash', () => {
		const src = readFileSync(resolve(ROOT, 'diagrams/+page.ts'), 'utf-8');
		expect(src).toMatch(/from '@sveltejs\/kit'/);
		expect(src).toMatch(/redirect\(308/);
		expect(src).toMatch(/['"`]\/views/);
		expect(src).toMatch(/url\.search/);
		expect(src).toMatch(/url\.hash/);
	});

	it('/diagrams/[id] issues a 308 redirect to /views/<id> preserving query + hash', () => {
		const src = readFileSync(resolve(ROOT, 'diagrams/[id]/+page.ts'), 'utf-8');
		expect(src).toMatch(/redirect\(308/);
		expect(src).toMatch(/['"`]\/views\//);
		expect(src).toMatch(/params\.id/);
		expect(src).toMatch(/url\.search/);
		expect(src).toMatch(/url\.hash/);
	});

	it('the in-app nav and Markdown click handler now point at /views', () => {
		const shell = readFileSync(resolve(ROOT, '../lib/components/AppShell.svelte'), 'utf-8');
		expect(shell).toMatch(/href:\s*'\/views'/);
		const md = readFileSync(resolve(ROOT, '../lib/components/MarkdownView.svelte'), 'utf-8');
		expect(md).toMatch(/`\/views\/\$\{id\}`/);
	});
});
