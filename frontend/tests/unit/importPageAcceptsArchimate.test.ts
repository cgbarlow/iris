import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Static-parser tests for the import page — confirms the v5.6.0 ArchiMate
 * Open Exchange wiring is in place: file picker advertises the new
 * extensions, the help text mentions ArchiMate, and the upload routes to
 * the new /api/import/archimate endpoint.
 */
describe('import page accepts ArchiMate OEX files', () => {
	const src = readFileSync(
		resolve(__dirname, '../../src/routes/import/+page.svelte'),
		'utf-8',
	);

	it('file input accept attribute includes archimate extensions', () => {
		expect(src).toMatch(/accept="[^"]*\.archimate[^"]*"/);
		expect(src).toMatch(/accept="[^"]*\.oex[^"]*"/);
		expect(src).toMatch(/accept="[^"]*\.xml[^"]*"/);
	});

	it('help text mentions ArchiMate Open Exchange', () => {
		expect(src).toContain('ArchiMate Open Exchange');
	});

	it('uploads route to /api/import/archimate when file is archimate', () => {
		expect(src).toContain('/api/import/archimate');
		expect(src).toContain('isArchimate');
	});

	it('selectFiles error message lists ArchiMate as a supported format', () => {
		expect(src).toMatch(/Supported formats:[^']*ArchiMate/);
	});
});
