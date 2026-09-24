/**
 * ADR-248 (v6.50.1): the diagram view hydrates its canvas nodes and
 * inherited tags from ONE `GET /api/diagrams/{id}/elements` response
 * instead of `GET /api/elements/{id}` per node (4x per node on first
 * visit). These are the pure pieces that turn that response into
 * canvas state.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';
import {
	hasLinkedElements,
	hydrateCanvasNodes,
	inheritedTagsFromElements,
} from '$lib/canvas/diagramElementHydration';
import type { Element } from '$lib/types/api';
import type { CanvasNode } from '$lib/types/canvas';

function element(id: string, overrides: Partial<Element> = {}): Element {
	return {
		id,
		element_type: 'class',
		current_version: 1,
		name: `Name ${id}`,
		description: `Desc ${id}`,
		data: {},
		created_at: '2026-09-23T00:00:00Z',
		created_by: 'u1',
		updated_at: '2026-09-23T00:00:00Z',
		is_deleted: false,
		diagram_usage_count: 1,
		...overrides,
	};
}

function node(id: string, data: Record<string, unknown>): CanvasNode {
	return { id, type: 'class', position: { x: 0, y: 0 }, data } as CanvasNode;
}

describe('hasLinkedElements', () => {
	it('is true when any node carries an entityId', () => {
		expect(hasLinkedElements([node('a', { label: 'x' }), node('b', { entityId: 'e1' })])).toBe(true);
	});

	it('is false for free-text-only or empty canvases (no request needed)', () => {
		expect(hasLinkedElements([])).toBe(false);
		expect(hasLinkedElements([node('a', { label: 'x' }), node('b', { entityId: '' })])).toBe(false);
	});
});

describe('hydrateCanvasNodes', () => {
	it('refreshes content fields from the matching element by entityId', () => {
		const nodes = [
			node('n1', { entityId: 'e1', label: 'Stale', description: 'old', diagramUsageCount: 0 }),
		];
		const els = [
			element('e1', {
				name: 'Fresh',
				description: 'new body',
				diagram_usage_count: 3,
				data: { attributes: [{ name: 'id' }] },
			}),
		];
		const { nodes: out, updated } = hydrateCanvasNodes(nodes, els);
		expect(updated).toBe(true);
		expect(out[0].data.label).toBe('Fresh');
		expect(out[0].data.description).toBe('new body');
		expect(out[0].data.diagramUsageCount).toBe(3);
		expect(out[0].data.attributes).toEqual([{ name: 'id' }]);
	});

	it('hydrates every node that shares an entityId from the single fetched element', () => {
		const nodes = [node('n1', { entityId: 'e1', label: 'a' }), node('n2', { entityId: 'e1', label: 'b' })];
		const { nodes: out } = hydrateCanvasNodes(nodes, [element('e1', { name: 'Shared' })]);
		expect(out.map((n) => n.data.label)).toEqual(['Shared', 'Shared']);
	});

	it('keeps node presentation the diagram owns (ADR-230 F1)', () => {
		const visual = { fill: '#abcdef', width: 321 };
		const nodes = [
			node('n1', { entityId: 'e1', label: 'x', visual, notation: 'archimate', entityType: 'capability' }),
		];
		const els = [element('e1', { notation: 'uml', data: { visual: { fill: '#000000' } } })];
		const { nodes: out } = hydrateCanvasNodes(nodes, els);
		expect(out[0].data.visual).toEqual(visual);
		expect(out[0].data.notation).toBe('archimate');
		expect(out[0].data.entityType).toBe('capability');
	});

	it('trims a description that starts with the label (BPMN-style payloads)', () => {
		const nodes = [node('n1', { entityId: 'e1' })];
		const els = [element('e1', { name: 'Title', description: 'Title\n\nBody text' })];
		const { nodes: out } = hydrateCanvasNodes(nodes, els);
		expect(out[0].data.description).toBe('Body text');
	});

	it('leaves nodes without an entityId, or whose element was not returned, untouched', () => {
		const free = node('free', { label: 'Free text' });
		const gone = node('gone', { entityId: 'deleted', label: 'Stored label' });
		const { nodes: out, updated } = hydrateCanvasNodes([free, gone], [element('e1')]);
		expect(updated).toBe(false);
		expect(out[0]).toBe(free);
		expect(out[1]).toBe(gone);
	});

	it('reports no update (and keeps identity) when nothing visible changed', () => {
		const el = element('e1');
		const first = hydrateCanvasNodes([node('n1', { entityId: 'e1' })], [el]).nodes;
		const again = hydrateCanvasNodes(first, [el]);
		expect(again.updated).toBe(false);
		expect(again.nodes[0]).toBe(first[0]);
	});
});

describe('inheritedTagsFromElements', () => {
	it('unions element tags, drops the diagram own tags, and sorts', () => {
		const els = [
			element('e1', { tags: ['zeta', 'shared', 'alpha'] }),
			element('e2', { tags: ['alpha', 'beta'] }),
			element('e3'),
		];
		expect(inheritedTagsFromElements(els, ['shared'])).toEqual(['alpha', 'beta', 'zeta']);
	});

	it('is empty when no element carries tags', () => {
		expect(inheritedTagsFromElements([], [])).toEqual([]);
		expect(inheritedTagsFromElements([element('e1', { tags: [] })], [])).toEqual([]);
	});
});

describe('/views/[id] page wiring (ADR-248)', () => {
	const pageSrc = readFileSync(
		resolve(__dirname, '../../src/routes/views/[id]/+page.svelte'),
		'utf-8',
	);

	it('loads the diagram untracked so the theme store cannot re-run the effect', () => {
		// loadDiagram() reads areThemesLoaded() before its first await; called
		// straight from the $effect that subscribed the effect to the theme
		// store and loaded every diagram twice.
		expect(pageSrc).toMatch(/import \{[^}]*\buntrack\b[^}]*\} from 'svelte'/);
		expect(pageSrc).toContain('untrack(() => loadDiagram(id))');
	});

	// The load-time hydration path: loadDiagramElements() and the two
	// helpers it drives, up to the next unrelated loader.
	const start = pageSrc.indexOf('async function loadDiagramElements(');
	const end = pageSrc.indexOf('async function loadAllTags(');
	const loadPath = pageSrc.slice(start, end);

	it('loadDiagram hydrates through loadDiagramElements after parsing the canvas', () => {
		const body = pageSrc.slice(pageSrc.indexOf('async function loadDiagram('));
		expect(body.indexOf('parseCanvasData()')).toBeGreaterThan(-1);
		expect(body.indexOf('loadDiagramElements(id)')).toBeGreaterThan(body.indexOf('parseCanvasData()'));
	});

	it('fetches canvas elements with one diagram-scoped request', () => {
		expect(start).toBeGreaterThan(-1);
		expect(end).toBeGreaterThan(start);
		expect(loadPath).toContain('/api/diagrams/${id}/elements');
		expect(loadPath).toContain('hydrateCanvasNodes(canvasNodes, elements)');
		expect(loadPath).toContain('inheritedTagsFromElements(elements');
	});

	it('no longer fetches an element per canvas node on load', () => {
		expect(loadPath).not.toContain('/api/elements/');
		expect(loadPath).not.toContain('Promise.all');
	});
});
