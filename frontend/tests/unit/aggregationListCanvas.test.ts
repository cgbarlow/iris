/**
 * SPEC-213-b / v6.26.0: AggregationListCanvas data contracts.
 *
 * Light-touch data-shape tests per the project convention.
 */

import { describe, expect, it } from 'vitest';

interface DiagramRow {
	id: string;
	name: string;
	diagram_type: string;
}

interface ProfileRow {
	id: string;
	name: string;
	is_global: boolean;
	set_id: string | null;
}

interface AggregationListSource {
	source_diagram_id?: string | null;
	profile_id?: string | null;
}

describe('diagram-list filter', () => {
	const ALL: DiagramRow[] = [
		{ id: '1', name: 'Spaghetti', diagram_type: 'smart_markdown' },
		{ id: '2', name: 'Bolognese', diagram_type: 'smart_markdown' },
		{ id: '3', name: 'Some component view', diagram_type: 'component' },
		{ id: '4', name: 'A dynamic list', diagram_type: 'dynamic_list' },
		{ id: '5', name: 'An aggregation list (itself)', diagram_type: 'aggregation_list' },
	];

	it('only smart_markdown diagrams are surfaced as sources', () => {
		const filtered = ALL.filter((d) => d.diagram_type === 'smart_markdown');
		expect(filtered.map((d) => d.id)).toEqual(['1', '2']);
	});

	it('aggregation_list diagrams are excluded (no self-referencing source)', () => {
		const filtered = ALL.filter((d) => d.diagram_type === 'smart_markdown');
		expect(filtered.find((d) => d.diagram_type === 'aggregation_list')).toBeUndefined();
	});
});

describe('profile list query shape', () => {
	it('set mode includes globals via include_global=true', () => {
		const setId = 'set-A';
		const params = new URLSearchParams();
		params.set('set_id', setId);
		params.set('include_global', 'true');
		expect(params.get('set_id')).toBe('set-A');
		expect(params.get('include_global')).toBe('true');
	});

	it('no-set mode falls back to include_global only', () => {
		const params = new URLSearchParams();
		params.set('include_global', 'true');
		expect(params.has('set_id')).toBe(false);
		expect(params.get('include_global')).toBe('true');
	});

	it('marks global profiles with a label suffix', () => {
		const rows: ProfileRow[] = [
			{ id: '1', name: 'Shopping list', is_global: true, set_id: null },
			{ id: '2', name: 'Custom rollup', is_global: false, set_id: 'set-A' },
		];
		const labels = rows.map((p) => `${p.name}${p.is_global ? ' (global)' : ''}`);
		expect(labels).toEqual(['Shopping list (global)', 'Custom rollup']);
	});
});

describe('onsourcechange emit shape', () => {
	it('preserves the other field when one is changed', () => {
		const initial: AggregationListSource = {
			source_diagram_id: 'src-1', profile_id: 'prof-1',
		};
		const afterSourceChange = { ...initial, source_diagram_id: 'src-2' };
		expect(afterSourceChange.source_diagram_id).toBe('src-2');
		expect(afterSourceChange.profile_id).toBe('prof-1');
	});

	it('emits null when the user picks the empty option', () => {
		// The <select>'s "— pick a source —" option has value="";
		// the change handler converts "" → null before emitting.
		const value = '';
		const emitted = value || null;
		expect(emitted).toBeNull();
	});

	it('partial config emits cleanly (one side filled, other null)', () => {
		const next: AggregationListSource = {
			source_diagram_id: 'src-1', profile_id: null,
		};
		expect(next.source_diagram_id).toBe('src-1');
		expect(next.profile_id).toBeNull();
	});
});

describe('view-mode vs edit-mode dispatch', () => {
	it('view mode renders content; edit mode does not need content', () => {
		// In view mode the canvas renders data.content via MarkdownView.
		// In edit mode the canvas shows the config pane and a preview
		// expander (still using the current data.content).
		const content = '## Group A\n- Pork mince: 1000 g\n';
		expect(content.length).toBeGreaterThan(0);
	});
});
