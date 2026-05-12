/**
 * ADR-158 (v5.13.0): admin AI prompts page filter logic and the
 * "Applies to" cascade label helper.
 *
 * The helper's job is to make ADR-132's intentional design (a
 * `layer=diagram_type` row with `notation=NULL` applies across all
 * notations) visually obvious — addresses the "ArchiMate Process
 * Layout has no notation set, why?" confusion the user reported.
 */

import { describe, expect, it } from 'vitest';

// Inline copy of the helper so tests don't pull in Svelte runtime;
// keep this in sync with `appliesToLabel` in
// `frontend/src/routes/admin/settings/ai/+page.svelte`.
function appliesToLabel(p: {
	layer: string;
	notation: string | null;
	diagram_type: string | null;
}): string {
	const n = p.notation || null;  // empty string → null
	const d = p.diagram_type || null;
	if (p.layer === 'base') return 'Any notation × Any diagram type';
	if (p.layer === 'override') {
		return n
			? `Override: ${n} (replaces all layers)`
			: 'Override (no notation set — invalid)';
	}
	if (p.layer === 'notation') {
		return n
			? `${n} × any diagram type`
			: 'Notation layer (no notation set — invalid)';
	}
	const notationPart = n ?? 'Any notation';
	const dtPart = d ?? '?';
	return `${notationPart} × ${dtPart} diagrams`;
}

describe('appliesToLabel — cascade UI hint', () => {
	it('base layer is universal', () => {
		expect(appliesToLabel({ layer: 'base', notation: null, diagram_type: null })).toBe(
			'Any notation × Any diagram type',
		);
	});

	it('notation layer with notation set names the notation', () => {
		expect(
			appliesToLabel({ layer: 'notation', notation: 'doview', diagram_type: null }),
		).toBe('doview × any diagram type');
	});

	it('override names the notation it replaces', () => {
		expect(
			appliesToLabel({ layer: 'override', notation: 'doview', diagram_type: null }),
		).toBe('Override: doview (replaces all layers)');
	});

	it('diagram_type layer with NULL notation explicitly says "Any notation"', () => {
		// This is the row the user found confusing — "ArchiMate Process Layout"
		// in the seed data has notation=NULL because it applies to ANY notation
		// that has the `process` diagram_type. The label needs to say that
		// explicitly so the cascade design is visible.
		expect(
			appliesToLabel({ layer: 'diagram_type', notation: null, diagram_type: 'process' }),
		).toBe('Any notation × process diagrams');
	});

	it('diagram_type layer with notation specifies both axes', () => {
		expect(
			appliesToLabel({
				layer: 'diagram_type',
				notation: 'archimate',
				diagram_type: 'process',
			}),
		).toBe('archimate × process diagrams');
	});

	it('diagram_type layer with empty notation behaves like NULL', () => {
		expect(
			appliesToLabel({ layer: 'diagram_type', notation: '', diagram_type: 'class' }),
		).toBe('Any notation × class diagrams');
	});
});

describe('Filter logic', () => {
	type Row = {
		id: string;
		name: string;
		description: string | null;
		purpose: string;
		layer: string;
		notation: string | null;
		diagram_type: string | null;
		is_active: boolean;
	};

	function applyFilters(
		rows: Row[],
		filters: {
			purpose?: string;
			layer?: string;
			notation?: string;
			diagramType?: string;
			status?: '' | 'active' | 'inactive';
			search?: string;
		},
	): Row[] {
		const q = (filters.search ?? '').toLowerCase().trim();
		return rows.filter((p) => {
			if (filters.purpose && (p.purpose ?? 'creation_format') !== filters.purpose) return false;
			if (filters.layer && p.layer !== filters.layer) return false;
			if (filters.notation && (p.notation ?? '') !== filters.notation) return false;
			if (filters.diagramType && (p.diagram_type ?? '') !== filters.diagramType) return false;
			if (filters.status === 'active' && !p.is_active) return false;
			if (filters.status === 'inactive' && p.is_active) return false;
			if (q) {
				if (
					!p.name.toLowerCase().includes(q)
					&& !(p.description?.toLowerCase().includes(q) ?? false)
				) {
					return false;
				}
			}
			return true;
		});
	}

	const sample: Row[] = [
		{ id: '1', name: 'A', description: null, purpose: 'creation_format', layer: 'base', notation: null, diagram_type: null, is_active: true },
		{ id: '2', name: 'B', description: 'doview methodology', purpose: 'creation_format', layer: 'notation', notation: 'doview', diagram_type: null, is_active: true },
		{ id: '3', name: 'C', description: null, purpose: 'response_format', layer: 'diagram_type', notation: null, diagram_type: 'doview_analysis', is_active: false },
		{ id: '4', name: 'D', description: null, purpose: 'response_format', layer: 'base', notation: null, diagram_type: null, is_active: true },
	];

	it('filter by purpose', () => {
		expect(applyFilters(sample, { purpose: 'response_format' }).map(r => r.id)).toEqual(['3', '4']);
	});

	it('filter by layer', () => {
		expect(applyFilters(sample, { layer: 'base' }).map(r => r.id)).toEqual(['1', '4']);
	});

	it('filter by status active', () => {
		expect(applyFilters(sample, { status: 'active' }).map(r => r.id)).toEqual(['1', '2', '4']);
	});

	it('filter by status inactive', () => {
		expect(applyFilters(sample, { status: 'inactive' }).map(r => r.id)).toEqual(['3']);
	});

	it('search matches name or description', () => {
		expect(applyFilters(sample, { search: 'doview' }).map(r => r.id)).toEqual(['2']);
	});

	it('combined filters narrow the result', () => {
		expect(
			applyFilters(sample, { purpose: 'response_format', status: 'active' }).map(r => r.id),
		).toEqual(['4']);
	});
});

describe('Conflict detection logic', () => {
	type Row = {
		id: string;
		purpose: string;
		layer: string;
		notation: string | null;
		diagram_type: string | null;
		is_active: boolean;
		name: string;
	};

	function findActiveConflict(
		rows: Row[],
		candidate: { purpose: string; layer: string; notation: string; diagram_type: string },
	): Row | null {
		return rows.find((p) =>
			p.is_active
			&& (p.purpose ?? 'creation_format') === candidate.purpose
			&& p.layer === candidate.layer
			&& (p.notation ?? '') === candidate.notation
			&& (p.diagram_type ?? '') === candidate.diagram_type,
		) ?? null;
	}

	const rows: Row[] = [
		{ id: 'existing-active', name: 'Existing', purpose: 'creation_format', layer: 'diagram_type', notation: null, diagram_type: 'outcomes_map', is_active: true },
		{ id: 'existing-inactive', name: 'Old', purpose: 'creation_format', layer: 'diagram_type', notation: null, diagram_type: 'outcomes_map', is_active: false },
	];

	it('detects conflict on same tuple as active row', () => {
		const conflict = findActiveConflict(rows, {
			purpose: 'creation_format', layer: 'diagram_type', notation: '', diagram_type: 'outcomes_map',
		});
		expect(conflict?.id).toBe('existing-active');
	});

	it('does not conflict when only an inactive row matches', () => {
		const conflict = findActiveConflict(
			rows.filter((r) => !r.is_active),
			{ purpose: 'creation_format', layer: 'diagram_type', notation: '', diagram_type: 'outcomes_map' },
		);
		expect(conflict).toBeNull();
	});

	it('does not conflict when notation differs', () => {
		const conflict = findActiveConflict(rows, {
			purpose: 'creation_format', layer: 'diagram_type', notation: 'simple', diagram_type: 'outcomes_map',
		});
		expect(conflict).toBeNull();
	});
});
