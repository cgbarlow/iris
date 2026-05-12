/**
 * v5.17.0 (ADR-162) — admin /admin/settings/ai filter dropdowns
 * cascade so an admin can't pick incompatible (notation, diagram_type)
 * combinations.
 *
 * Inline copies of the helpers; keep in sync with
 * `frontend/src/routes/admin/settings/ai/+page.svelte`.
 */
import { describe, it, expect } from 'vitest';

type NotationMapping = { notation_id: string; notation_name?: string; is_default?: boolean };
type DiagramType = { id: string; name: string; notations?: NotationMapping[] };
type Notation = { id: string; name: string };

function compatibleDiagramTypes(
	notationId: string | null,
	allDts: DiagramType[],
): DiagramType[] {
	if (!notationId) return allDts;
	return allDts.filter((dt) =>
		(dt.notations ?? []).some((n) => n.notation_id === notationId),
	);
}

function compatibleNotations(
	dtId: string | null,
	allDts: DiagramType[],
	allNotations: Notation[],
): Notation[] {
	if (!dtId) return allNotations;
	const dt = allDts.find((d) => d.id === dtId);
	if (!dt || !dt.notations || dt.notations.length === 0) return allNotations;
	const validIds = new Set(dt.notations.map((n) => n.notation_id));
	return allNotations.filter((n) => validIds.has(n.id));
}

const NOTATIONS: Notation[] = [
	{ id: 'simple', name: 'Simple' },
	{ id: 'doview', name: 'DoView' },
	{ id: 'c4', name: 'C4' },
	{ id: 'markdown', name: 'Markdown' },
];

const DIAGRAM_TYPES: DiagramType[] = [
	{ id: 'outcomes_map', name: 'Outcomes Map', notations: [{ notation_id: 'doview' }] },
	{ id: 'overview', name: 'Overview', notations: [{ notation_id: 'doview' }] },
	{ id: 'container', name: 'Container', notations: [{ notation_id: 'c4' }] },
	{ id: 'doview_analysis', name: 'DoView Analysis', notations: [{ notation_id: 'markdown' }] },
	{ id: 'component', name: 'Component', notations: [{ notation_id: 'simple' }, { notation_id: 'c4' }] },
];

describe('compatibleDiagramTypes — Notation → Diagram type cascade', () => {
	it('returns every diagram_type when no notation filter is set', () => {
		expect(compatibleDiagramTypes(null, DIAGRAM_TYPES)).toEqual(DIAGRAM_TYPES);
	});

	it('filters to doview-compatible types when notation=doview', () => {
		const result = compatibleDiagramTypes('doview', DIAGRAM_TYPES);
		expect(result.map((d) => d.id)).toEqual(['outcomes_map', 'overview']);
	});

	it('includes multi-notation types like component (simple + c4)', () => {
		const c4 = compatibleDiagramTypes('c4', DIAGRAM_TYPES).map((d) => d.id);
		expect(c4).toContain('container');
		expect(c4).toContain('component');
		const simple = compatibleDiagramTypes('simple', DIAGRAM_TYPES).map((d) => d.id);
		expect(simple).toEqual(['component']);
	});
});

describe('compatibleNotations — Diagram type → Notation cascade', () => {
	it('returns every notation when no diagram_type filter is set', () => {
		expect(compatibleNotations(null, DIAGRAM_TYPES, NOTATIONS)).toEqual(NOTATIONS);
	});

	it('filters to a diagram_types compatible notations', () => {
		const r = compatibleNotations('outcomes_map', DIAGRAM_TYPES, NOTATIONS);
		expect(r.map((n) => n.id)).toEqual(['doview']);
	});

	it('returns multi-notation set when diagram_type has multiple', () => {
		const r = compatibleNotations('component', DIAGRAM_TYPES, NOTATIONS);
		expect(r.map((n) => n.id).sort()).toEqual(['c4', 'simple']);
	});

	it('returns all when diagram_type has no notations field (defensive)', () => {
		const dts: DiagramType[] = [{ id: 'lonely', name: 'Lonely' }];
		const r = compatibleNotations('lonely', dts, NOTATIONS);
		expect(r).toEqual(NOTATIONS);
	});
});
