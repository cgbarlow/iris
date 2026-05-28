import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Static-parser tests for the import page — confirms the v6.32.0 Sparx EA
 * native XMI wiring: `.xml` uploads are content-sniffed so a Sparx native
 * XMI export routes to /api/import/sparx-xml while ArchiMate Open Exchange
 * still routes to /api/import/archimate (ADR-219).
 */
describe('import page routes Sparx EA native XMI', () => {
	const src = readFileSync(
		resolve(__dirname, '../../src/routes/import/+page.svelte'),
		'utf-8',
	);

	it('has a content-sniff resolver for the shared .xml extension', () => {
		expect(src).toContain('resolveXmlEndpoint');
		// Sniff markers that identify a Sparx EA native XMI export.
		expect(src).toContain('sparxsystems.com');
		expect(src).toContain('Enterprise Architect');
	});

	it('routes sniffed Sparx XMI to /api/import/sparx-xml', () => {
		expect(src).toContain('/api/import/sparx-xml');
	});

	it('still routes ArchiMate OEX to /api/import/archimate', () => {
		expect(src).toContain('/api/import/archimate');
	});

	it('help text mentions Sparx native XML/XMI', () => {
		expect(src).toMatch(/native XML\/XMI|native XMI/);
	});
});
