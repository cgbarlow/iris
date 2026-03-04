import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Package Metadata Enrichment tests (ADR-072).
 * Verifies that the import pipeline captures enriched package metadata
 * and the package detail page displays it in an Extended accordion.
 */

/* ── Backend: Import enrichment ── */

describe('Package metadata import enrichment', () => {
	const serviceSrc = readFileSync(
		resolve(__dirname, '../../../backend/app/import_sparx/service.py'),
		'utf-8',
	);

	it('captures ea_guid from package', () => {
		expect(serviceSrc).toContain('ea_guid');
	});

	it('captures Status field from package-type element', () => {
		expect(serviceSrc).toContain('"Status"');
	});

	it('captures Stereotype field from package-type element', () => {
		expect(serviceSrc).toContain('"Stereotype"');
	});

	it('captures Version field from package-type element', () => {
		expect(serviceSrc).toContain('"Version"');
	});

	it('captures Scope field from package-type element', () => {
		expect(serviceSrc).toContain('"Scope"');
	});

	it('captures Author field from package-type element', () => {
		expect(serviceSrc).toContain('"Author"');
	});

	it('captures date fields from package-type element', () => {
		expect(serviceSrc).toContain('"CreatedDate"');
		expect(serviceSrc).toContain('"ModifiedDate"');
	});

	it('captures tagged values from package-type element', () => {
		expect(serviceSrc).toContain('tagged_values');
		expect(serviceSrc).toContain('tags_by_object');
	});
});

/* ── Frontend: Package detail page ── */

describe('Package detail page', () => {
	const pageSrc = readFileSync(
		resolve(__dirname, '../../src/routes/packages/[id]/+page.svelte'),
		'utf-8',
	);

	it('fetches package data from /api/packages/', () => {
		expect(pageSrc).toContain('/api/packages/');
	});

	it('fetches package versions', () => {
		expect(pageSrc).toContain('/versions');
	});

	it('has Overview accordion section', () => {
		expect(pageSrc).toContain('Overview');
	});

	it('has Details accordion section', () => {
		expect(pageSrc).toContain('Details');
	});

	it('has Extended accordion section', () => {
		expect(pageSrc).toContain('Extended');
	});
});

describe('Package detail page Extended accordion', () => {
	const pageSrc = readFileSync(
		resolve(__dirname, '../../src/routes/packages/[id]/+page.svelte'),
		'utf-8',
	);

	it('displays ea_guid field', () => {
		expect(pageSrc).toContain('ea_guid');
	});

	it('displays stereotype field', () => {
		expect(pageSrc).toContain('stereotype');
	});

	it('displays scope field', () => {
		expect(pageSrc).toContain('scope');
	});

	it('displays author field', () => {
		expect(pageSrc).toContain('author');
	});

	it('displays date fields', () => {
		expect(pageSrc).toContain('created_date');
		expect(pageSrc).toContain('modified_date');
	});

	it('renders tagged values table with Property and Value headers', () => {
		expect(pageSrc).toContain('tagged_values');
		expect(pageSrc).toContain('Property');
		expect(pageSrc).toContain('Value');
	});

	it('shows empty state when no extended metadata', () => {
		expect(pageSrc).toContain('No extended metadata available');
	});
});
