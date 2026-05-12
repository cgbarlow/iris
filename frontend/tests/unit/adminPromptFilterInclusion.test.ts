/**
 * v5.17.0 (ADR-162) — `isNotationScopeMatch` lets the admin AI
 * prompts table show diagram_type-layer rows whose `notation` is
 * null but whose `diagram_type` maps to the selected notation via
 * diagram_type_notations. Fixes "selecting doview shows only 1
 * prompt" because the previous exact-match predicate excluded those
 * indirect rows.
 *
 * Notation-agnostic: works the same way for every notation.
 *
 * Inline copy of the predicate; keep in sync with
 * `frontend/src/routes/admin/settings/ai/+page.svelte`.
 */
import { describe, it, expect } from 'vitest';

type NotationMapping = { notation_id: string };
type DiagramType = { id: string; name: string; notations?: NotationMapping[] };

function isNotationScopeMatch(
	p: { notation: string | null; diagram_type: string | null },
	notationFilterValue: string,
	allDts: DiagramType[],
): boolean {
	if (!notationFilterValue) return true;
	if ((p.notation ?? '') === notationFilterValue) return true;
	if (!p.diagram_type) return false;
	const dt = allDts.find((d) => d.id === p.diagram_type);
	return !!(dt?.notations ?? []).some((n) => n.notation_id === notationFilterValue);
}

const DTS: DiagramType[] = [
	{ id: 'outcomes_map', name: 'Outcomes Map', notations: [{ notation_id: 'doview' }] },
	{ id: 'overview', name: 'Overview', notations: [{ notation_id: 'doview' }] },
	{ id: 'doview_analysis', name: 'DoView Analysis', notations: [{ notation_id: 'markdown' }] },
];

describe('isNotationScopeMatch — admin AI prompts row inclusion', () => {
	it('returns every row when filter is empty', () => {
		const p = { notation: null, diagram_type: null };
		expect(isNotationScopeMatch(p, '', DTS)).toBe(true);
	});

	it('matches direct notation (layer=notation, layer=override row)', () => {
		// creation-doview-notation-v1: notation='doview', diagram_type=null
		const p = { notation: 'doview', diagram_type: null };
		expect(isNotationScopeMatch(p, 'doview', DTS)).toBe(true);
	});

	it('matches indirect via diagram_type_notations (layer=diagram_type row)', () => {
		// creation-outcomes-map-v1: notation=null, diagram_type='outcomes_map'
		// — outcomes_map maps to doview, so should appear under notation=doview.
		const p = { notation: null, diagram_type: 'outcomes_map' };
		expect(isNotationScopeMatch(p, 'doview', DTS)).toBe(true);
	});

	it('excludes base-layer rows from notation-specific filters', () => {
		// creation-base-v1: notation=null, diagram_type=null
		const p = { notation: null, diagram_type: null };
		expect(isNotationScopeMatch(p, 'doview', DTS)).toBe(false);
	});

	it('excludes unrelated-notation rows', () => {
		// A markdown notation-layer row should not appear under notation=doview.
		const p = { notation: 'markdown', diagram_type: null };
		expect(isNotationScopeMatch(p, 'doview', DTS)).toBe(false);
	});

	it('excludes diagram_types not mapped to the filter notation', () => {
		// doview_analysis maps to markdown, not doview.
		const p = { notation: null, diagram_type: 'doview_analysis' };
		expect(isNotationScopeMatch(p, 'doview', DTS)).toBe(false);
	});

	it('reproduces the v5.17.0 fix-target: doview filter shows all 3 doview-relevant rows', () => {
		// Three doview-relevant rows from v5.8.x+:
		const rows = [
			{ id: 'creation-doview-notation-v1', notation: 'doview', diagram_type: null },
			{ id: 'creation-outcomes-map-v1', notation: null, diagram_type: 'outcomes_map' },
			{ id: 'creation-doview-overview-v1', notation: null, diagram_type: 'overview' },
		];
		const matched = rows.filter((p) => isNotationScopeMatch(p, 'doview', DTS));
		expect(matched.map((r) => r.id)).toEqual([
			'creation-doview-notation-v1',
			'creation-outcomes-map-v1',
			'creation-doview-overview-v1',
		]);
	});
});
