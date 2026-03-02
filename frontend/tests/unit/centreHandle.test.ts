// @ts-nocheck — Node.js imports (fs, path) not typed under SvelteKit tsconfig; Vitest resolves them correctly at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve, join } from 'node:path';

/**
 * Tests for centre-point connection handle (ADR-053).
 *
 * Verifies all 15 node components (8 Simple View, 6 UML, 1 ArchiMate)
 * contain a centre Handle with id="center" and class="center-handle".
 */

const ROOT = resolve(__dirname, '../../src/lib/canvas');

const SIMPLE_VIEW_NODES = [
	'nodes/ActorNode.svelte',
	'nodes/ComponentNode.svelte',
	'nodes/DatabaseNode.svelte',
	'nodes/InterfaceNode.svelte',
	'nodes/ModelRefNode.svelte',
	'nodes/PackageNode.svelte',
	'nodes/QueueNode.svelte',
	'nodes/ServiceNode.svelte',
];

const UML_NODES = [
	'uml/nodes/ActivityNode.svelte',
	'uml/nodes/ClassNode.svelte',
	'uml/nodes/DeploymentNode.svelte',
	'uml/nodes/ObjectNode.svelte',
	'uml/nodes/StateNode.svelte',
	'uml/nodes/UseCaseNode.svelte',
];

const ARCHIMATE_NODES = [
	'archimate/nodes/ArchimateNode.svelte',
];

const ALL_NODES = [...SIMPLE_VIEW_NODES, ...UML_NODES, ...ARCHIMATE_NODES];

describe('Centre-point connection handle (ADR-053)', () => {
	it.each(ALL_NODES)('%s contains a centre Handle with id="center"', (relPath) => {
		const filePath = join(ROOT, relPath);
		const source = readFileSync(filePath, 'utf-8');
		expect(source).toContain('id="center"');
		expect(source).toContain('class="center-handle"');
	});

	it('all 15 node components are covered', () => {
		expect(ALL_NODES).toHaveLength(15);
	});

	it.each(ALL_NODES)('%s centre handle uses type="source"', (relPath) => {
		const filePath = join(ROOT, relPath);
		const source = readFileSync(filePath, 'utf-8');
		// Find the centre handle line and verify it uses type="source"
		const lines = source.split('\n');
		const centreLine = lines.find((l: string) => l.includes('id="center"'));
		expect(centreLine).toBeDefined();
		expect(centreLine).toContain('type="source"');
	});

	it.each(ALL_NODES)('%s centre handle is positioned at 50%%/50%%', (relPath) => {
		const filePath = join(ROOT, relPath);
		const source = readFileSync(filePath, 'utf-8');
		const lines = source.split('\n');
		const centreLine = lines.find((l: string) => l.includes('id="center"'));
		expect(centreLine).toBeDefined();
		expect(centreLine).toContain('left:50%');
		expect(centreLine).toContain('top:50%');
	});
});
