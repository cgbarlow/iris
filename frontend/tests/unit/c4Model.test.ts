import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * C4 Model Support tests (ADR-074).
 * Verifies C4 element types, relationship types, renderers, and registry.
 */

/* ── C4 type definitions ── */

describe('C4 type definitions', () => {
	const typesSrc = readFileSync(
		resolve(__dirname, '../../src/lib/types/canvas.ts'),
		'utf-8',
	);

	it('defines C4EntityType union', () => {
		expect(typesSrc).toContain('C4EntityType');
	});

	it('includes person element type', () => {
		expect(typesSrc).toContain("'person'");
	});

	it('includes software_system element type', () => {
		expect(typesSrc).toContain("'software_system'");
	});

	it('includes software_system_external element type', () => {
		expect(typesSrc).toContain("'software_system_external'");
	});

	it('includes container element type', () => {
		expect(typesSrc).toContain("'container'");
	});

	it('includes c4_component element type', () => {
		expect(typesSrc).toContain("'c4_component'");
	});

	it('includes deployment_node element type', () => {
		expect(typesSrc).toContain("'deployment_node'");
	});

	it('includes infrastructure_node element type', () => {
		expect(typesSrc).toContain("'infrastructure_node'");
	});

	it('includes container_instance element type', () => {
		expect(typesSrc).toContain("'container_instance'");
	});

	it('defines C4Level type', () => {
		expect(typesSrc).toContain('C4Level');
	});

	it('defines C4_ENTITY_TYPES array', () => {
		expect(typesSrc).toContain('C4_ENTITY_TYPES');
	});

	it('defines C4RelationshipType', () => {
		expect(typesSrc).toContain('C4RelationshipType');
	});

	it('defines C4_RELATIONSHIP_TYPES array', () => {
		expect(typesSrc).toContain('C4_RELATIONSHIP_TYPES');
	});

	it('includes c4_relationship type', () => {
		expect(typesSrc).toContain("'c4_relationship'");
	});
});

/* ── Registry ── */

describe('C4 registry', () => {
	const registrySrc = readFileSync(
		resolve(__dirname, '../../src/lib/canvas/registry.ts'),
		'utf-8',
	);

	it('includes C4 node types in ALL_NODE_TYPE_KEYS', () => {
		expect(registrySrc).toContain("'person'");
		expect(registrySrc).toContain("'software_system'");
		expect(registrySrc).toContain("'c4_component'");
		expect(registrySrc).toContain("'deployment_node'");
	});

	it('includes C4 edge type in ALL_EDGE_TYPE_KEYS', () => {
		expect(registrySrc).toContain("'c4_relationship'");
	});

	it('has C4 type equivalences', () => {
		expect(registrySrc).toContain("c4: 'c4_component'");
		expect(registrySrc).toContain("c4: 'person'");
	});
});

/* ── DynamicNode C4 dispatch ── */

describe('DynamicNode C4 dispatch', () => {
	const dynamicNodeSrc = readFileSync(
		resolve(__dirname, '../../src/lib/canvas/DynamicNode.svelte'),
		'utf-8',
	);

	it('imports C4Renderer', () => {
		expect(dynamicNodeSrc).toContain('C4Renderer');
	});

	it('defines C4_TYPES set', () => {
		expect(dynamicNodeSrc).toContain('C4_TYPES');
	});

	it('dispatches to C4Renderer for c4 notation', () => {
		expect(dynamicNodeSrc).toContain("notation === 'c4'");
	});
});

/* ── DynamicEdge C4 dispatch ── */

describe('DynamicEdge C4 dispatch', () => {
	const dynamicEdgeSrc = readFileSync(
		resolve(__dirname, '../../src/lib/canvas/DynamicEdge.svelte'),
		'utf-8',
	);

	it('imports C4EdgeRenderer', () => {
		expect(dynamicEdgeSrc).toContain('C4EdgeRenderer');
	});

	it('defines C4_TYPES set for edges', () => {
		expect(dynamicEdgeSrc).toContain('C4_TYPES');
	});

	it('dispatches to C4EdgeRenderer for c4 notation', () => {
		expect(dynamicEdgeSrc).toContain("notation === 'c4'");
	});
});

/* ── C4Renderer ── */

describe('C4Renderer', () => {
	const rendererSrc = readFileSync(
		resolve(__dirname, '../../src/lib/canvas/renderers/C4Renderer.svelte'),
		'utf-8',
	);

	it('renders with BaseNode', () => {
		expect(rendererSrc).toContain('BaseNode');
	});

	it('has icons for all C4 types', () => {
		expect(rendererSrc).toContain("person:");
		expect(rendererSrc).toContain("software_system:");
		expect(rendererSrc).toContain("container:");
		expect(rendererSrc).toContain("c4_component:");
		expect(rendererSrc).toContain("deployment_node:");
	});

	it('has level labels', () => {
		expect(rendererSrc).toContain('C4_LEVELS');
	});

	it('uses c4-node CSS class', () => {
		expect(rendererSrc).toContain('c4-node');
	});

	it('has dark mode styles', () => {
		expect(rendererSrc).toContain(':global(.dark)');
	});
});

/* ── C4EdgeRenderer ── */

describe('C4EdgeRenderer', () => {
	const rendererSrc = readFileSync(
		resolve(__dirname, '../../src/lib/canvas/renderers/C4EdgeRenderer.svelte'),
		'utf-8',
	);

	it('renders with IrisBaseEdge', () => {
		expect(rendererSrc).toContain('IrisBaseEdge');
	});

	it('uses solid lines', () => {
		expect(rendererSrc).toContain("'none'");
	});
});
