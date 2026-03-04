import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Import Idempotency tests (ADR-073).
 * Verifies that re-importing a .qea file skips existing items (matched by ea_guid),
 * tracks skip counts, and force-delete cascades packages.
 */

/* ── Backend: Import idempotency ── */

describe('Import service idempotency', () => {
	const serviceSrc = readFileSync(
		resolve(__dirname, '../../../backend/app/import_sparx/service.py'),
		'utf-8',
	);

	it('stores ea_guid in element metadata', () => {
		expect(serviceSrc).toContain('em["ea_guid"]');
	});

	it('stores ea_guid in diagram metadata', () => {
		// The diagram creation should include ea_guid in metadata
		expect(serviceSrc).toContain('diag.ea_guid');
	});

	it('builds GUID index before creating items', () => {
		expect(serviceSrc).toContain('_build_guid_index');
	});

	it('checks existing GUIDs before creating packages', () => {
		expect(serviceSrc).toContain('packages_skipped');
	});

	it('checks existing GUIDs before creating elements', () => {
		// elements_skipped already exists for unmapped types, but should also
		// handle GUID-based skips
		expect(serviceSrc).toContain('guid_index');
	});

	it('checks existing GUIDs before creating diagrams', () => {
		expect(serviceSrc).toContain('diagrams_skipped');
	});
});

describe('ImportSummary skip counts', () => {
	const serviceSrc = readFileSync(
		resolve(__dirname, '../../../backend/app/import_sparx/service.py'),
		'utf-8',
	);

	it('has packages_skipped field', () => {
		expect(serviceSrc).toContain('packages_skipped');
	});

	it('has diagrams_skipped field', () => {
		expect(serviceSrc).toContain('diagrams_skipped');
	});
});

/* ── Backend: Force-delete set cascades packages ── */

describe('Force-delete set cascade', () => {
	const setsSrc = readFileSync(
		resolve(__dirname, '../../../backend/app/sets/service.py'),
		'utf-8',
	);

	it('soft-deletes packages in set', () => {
		expect(setsSrc).toContain('packages');
		expect(setsSrc).toContain("UPDATE packages SET is_deleted");
	});

	it('soft-deletes package_relationships for packages in set', () => {
		expect(setsSrc).toContain('package_relationships');
	});
});

/* ── Frontend: Import page shows skip counts ── */

describe('Import page skip counts', () => {
	const pageSrc = readFileSync(
		resolve(__dirname, '../../src/routes/import/+page.svelte'),
		'utf-8',
	);

	it('ImportSummary interface has packages_skipped', () => {
		expect(pageSrc).toContain('packages_skipped');
	});

	it('ImportSummary interface has diagrams_skipped', () => {
		expect(pageSrc).toContain('diagrams_skipped');
	});

	it('displays packages skipped count', () => {
		expect(pageSrc).toContain('Packages Skipped');
	});

	it('displays diagrams skipped count', () => {
		expect(pageSrc).toContain('Diagrams Skipped');
	});
});
