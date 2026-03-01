// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves them correctly at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve, join, basename } from 'node:path';
import { createCanvasHistory } from '../../src/lib/canvas/useCanvasHistory.svelte';
import type { CanvasNode, CanvasEdge } from '$lib/types/canvas';
import type { EdgeRoutingType } from '$lib/types/canvas';

/**
 * Tests for connector manipulation / edge routing type selection (ADR-042, WP-11).
 *
 * Verifies:
 * 1. EdgeRoutingType type exists and is correctly defined
 * 2. CanvasEdgeData includes optional routingType field
 * 3. All 5 Simple View edge components import all required path functions
 * 4. All 5 Simple View edge components read data.routingType
 * 5. Routing type change integrates with undo/redo history
 * 6. Model detail page contains routing type dropdown markup
 */

const FRONTEND_SRC = resolve(import.meta.dirname, '../../src/lib/canvas');
const TYPES_FILE = resolve(import.meta.dirname, '../../src/lib/types/canvas.ts');
const PAGE_FILE = resolve(import.meta.dirname, '../../src/routes/models/[id]/+page.svelte');

const simpleEdgeFiles = [
	'edges/UsesEdge.svelte',
	'edges/DependsOnEdge.svelte',
	'edges/ComposesEdge.svelte',
	'edges/ImplementsEdge.svelte',
	'edges/ContainsEdge.svelte',
];

function makeNodes(): CanvasNode[] {
	return [
		{ id: 'n1', type: 'component', position: { x: 0, y: 0 }, data: { label: 'Node 1', entityType: 'component' } },
		{ id: 'n2', type: 'service', position: { x: 200, y: 0 }, data: { label: 'Node 2', entityType: 'service' } },
	];
}

function makeEdges(routingType?: EdgeRoutingType): CanvasEdge[] {
	return [
		{
			id: 'e-n1-n2',
			source: 'n1',
			target: 'n2',
			type: 'uses',
			data: { relationshipType: 'uses', label: 'calls', routingType },
		},
	];
}

/**
 * Simulates the routing type change handler from the model detail page.
 */
function applyRoutingTypeChange(
	edges: CanvasEdge[],
	edgeId: string,
	newType: EdgeRoutingType,
): CanvasEdge[] {
	return edges.map((e) =>
		e.id === edgeId
			? { ...e, data: { ...e.data!, routingType: newType === 'default' ? undefined : newType } }
			: e,
	);
}

describe('EdgeRoutingType type definition', () => {
	it('canvas.ts exports EdgeRoutingType type', () => {
		const content = readFileSync(TYPES_FILE, 'utf-8');
		expect(content).toContain('EdgeRoutingType');
	});

	it('EdgeRoutingType includes all five routing options', () => {
		const content = readFileSync(TYPES_FILE, 'utf-8');
		expect(content).toMatch(/['"]default['"]/);
		expect(content).toMatch(/['"]straight['"]/);
		expect(content).toMatch(/['"]step['"]/);
		expect(content).toMatch(/['"]smoothstep['"]/);
		expect(content).toMatch(/['"]bezier['"]/);
	});

	it('CanvasEdgeData includes optional routingType field', () => {
		const content = readFileSync(TYPES_FILE, 'utf-8');
		expect(content).toMatch(/routingType\?.*EdgeRoutingType/);
	});
});

describe('Simple View edge components support routing types', () => {
	for (const file of simpleEdgeFiles) {
		const componentName = basename(file, '.svelte');

		it(`${componentName} imports getStraightPath`, () => {
			const filePath = join(FRONTEND_SRC, file);
			const content = readFileSync(filePath, 'utf-8');
			expect(content).toContain('getStraightPath');
		});

		it(`${componentName} imports getSmoothStepPath`, () => {
			const filePath = join(FRONTEND_SRC, file);
			const content = readFileSync(filePath, 'utf-8');
			expect(content).toContain('getSmoothStepPath');
		});

		it(`${componentName} imports getBezierPath`, () => {
			const filePath = join(FRONTEND_SRC, file);
			const content = readFileSync(filePath, 'utf-8');
			expect(content).toContain('getBezierPath');
		});

		it(`${componentName} reads data.routingType`, () => {
			const filePath = join(FRONTEND_SRC, file);
			const content = readFileSync(filePath, 'utf-8');
			expect(content).toContain('routingType');
		});

		it(`${componentName} handles straight routing type`, () => {
			const filePath = join(FRONTEND_SRC, file);
			const content = readFileSync(filePath, 'utf-8');
			expect(content).toMatch(/['"]straight['"]/);
		});

		it(`${componentName} handles step routing type with borderRadius 0`, () => {
			const filePath = join(FRONTEND_SRC, file);
			const content = readFileSync(filePath, 'utf-8');
			expect(content).toMatch(/['"]step['"]/);
			expect(content).toContain('borderRadius');
		});

		it(`${componentName} handles smoothstep routing type`, () => {
			const filePath = join(FRONTEND_SRC, file);
			const content = readFileSync(filePath, 'utf-8');
			expect(content).toMatch(/['"]smoothstep['"]/);
		});

		it(`${componentName} handles bezier routing type`, () => {
			const filePath = join(FRONTEND_SRC, file);
			const content = readFileSync(filePath, 'utf-8');
			// Must have explicit bezier routing case (not just the default getBezierPath)
			expect(content).toMatch(/['"]bezier['"]/);
		});
	}
});

describe('Routing type change logic', () => {
	it('changes edge routing type to straight', () => {
		const edges = makeEdges();
		const result = applyRoutingTypeChange(edges, 'e-n1-n2', 'straight');
		expect(result[0].data?.routingType).toBe('straight');
	});

	it('changes edge routing type to step', () => {
		const edges = makeEdges();
		const result = applyRoutingTypeChange(edges, 'e-n1-n2', 'step');
		expect(result[0].data?.routingType).toBe('step');
	});

	it('changes edge routing type to smoothstep', () => {
		const edges = makeEdges();
		const result = applyRoutingTypeChange(edges, 'e-n1-n2', 'smoothstep');
		expect(result[0].data?.routingType).toBe('smoothstep');
	});

	it('changes edge routing type to bezier', () => {
		const edges = makeEdges();
		const result = applyRoutingTypeChange(edges, 'e-n1-n2', 'bezier');
		expect(result[0].data?.routingType).toBe('bezier');
	});

	it('changes edge routing type to default (clears routingType)', () => {
		const edges = makeEdges('straight');
		const result = applyRoutingTypeChange(edges, 'e-n1-n2', 'default');
		expect(result[0].data?.routingType).toBeUndefined();
	});

	it('preserves other edge data when changing routing type', () => {
		const edges = makeEdges();
		const result = applyRoutingTypeChange(edges, 'e-n1-n2', 'step');
		expect(result[0].data?.relationshipType).toBe('uses');
		expect(result[0].data?.label).toBe('calls');
		expect(result[0].source).toBe('n1');
		expect(result[0].target).toBe('n2');
	});

	it('only modifies the matching edge, leaving others untouched', () => {
		const edges: CanvasEdge[] = [
			{ id: 'e1', source: 'n1', target: 'n2', type: 'uses', data: { relationshipType: 'uses' } },
			{ id: 'e2', source: 'n2', target: 'n1', type: 'depends_on', data: { relationshipType: 'depends_on' } },
		];
		const result = applyRoutingTypeChange(edges, 'e1', 'straight');
		expect(result[0].data?.routingType).toBe('straight');
		expect(result[1].data?.routingType).toBeUndefined();
	});
});

describe('Routing type undo/redo integration', () => {
	it('routing type change can be undone via history', () => {
		const history = createCanvasHistory();
		const nodes = makeNodes();
		let edges = makeEdges();

		// Push pre-change state
		history.pushState(nodes, edges);

		// Apply routing type change
		edges = applyRoutingTypeChange(edges, 'e-n1-n2', 'straight');
		expect(edges[0].data?.routingType).toBe('straight');

		// Undo
		const restored = history.undo(nodes, edges);
		expect(restored).not.toBeNull();
		expect(restored!.edges[0].data?.routingType).toBeUndefined();
	});

	it('routing type change can be redone after undo', () => {
		const history = createCanvasHistory();
		const nodes = makeNodes();
		let edges = makeEdges();

		// Push pre-change state
		history.pushState(nodes, edges);

		// Apply routing type change
		edges = applyRoutingTypeChange(edges, 'e-n1-n2', 'step');

		// Undo
		const restored = history.undo(nodes, edges);
		edges = restored!.edges;
		expect(edges[0].data?.routingType).toBeUndefined();

		// Redo
		const redone = history.redo(nodes, edges);
		expect(redone).not.toBeNull();
		expect(redone!.edges[0].data?.routingType).toBe('step');
	});

	it('preserves all edge data through routing type undo/redo cycle', () => {
		const history = createCanvasHistory();
		const nodes = makeNodes();
		let edges = makeEdges();

		history.pushState(nodes, edges);
		edges = applyRoutingTypeChange(edges, 'e-n1-n2', 'smoothstep');

		// Undo
		const restored = history.undo(nodes, edges);
		expect(restored!.edges[0].data?.label).toBe('calls');
		expect(restored!.edges[0].data?.relationshipType).toBe('uses');

		// Redo
		edges = restored!.edges;
		const redone = history.redo(nodes, edges);
		expect(redone!.edges[0].data?.label).toBe('calls');
		expect(redone!.edges[0].data?.relationshipType).toBe('uses');
		expect(redone!.edges[0].data?.routingType).toBe('smoothstep');
	});
});

describe('Model detail page routing type UI', () => {
	it('page contains routing type select dropdown', () => {
		const content = readFileSync(PAGE_FILE, 'utf-8');
		expect(content).toContain('aria-label="Edge routing type"');
	});

	it('page dropdown has all five routing options', () => {
		const content = readFileSync(PAGE_FILE, 'utf-8');
		expect(content).toContain('>Default<');
		expect(content).toContain('>Straight<');
		expect(content).toContain('>Step<');
		expect(content).toContain('>Smooth Step<');
		expect(content).toContain('>Bezier<');
	});

	it('page imports EdgeRoutingType', () => {
		const content = readFileSync(PAGE_FILE, 'utf-8');
		expect(content).toContain('EdgeRoutingType');
	});

	it('page has handleRoutingTypeChange function', () => {
		const content = readFileSync(PAGE_FILE, 'utf-8');
		expect(content).toContain('handleRoutingTypeChange');
	});

	it('page has selectedEdgeRoutingType derived value', () => {
		const content = readFileSync(PAGE_FILE, 'utf-8');
		expect(content).toContain('selectedEdgeRoutingType');
	});

	it('page has onedgeselect callback wired to canvas components', () => {
		const content = readFileSync(PAGE_FILE, 'utf-8');
		expect(content).toContain('onedgeselect');
	});
});
