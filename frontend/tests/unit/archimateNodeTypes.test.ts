// @ts-nocheck — Node.js imports not typed under SvelteKit tsconfig; Vitest resolves them correctly at runtime.
import { describe, it, expect } from 'vitest';
import { archimateNodeTypes } from '../../src/lib/canvas/archimate/nodes/index';

/**
 * Tests for ArchiMate seed data node type mapping (ADR-054).
 *
 * Verifies that all node types used in the Enterprise View seed model
 * exist in the archimateNodeTypes registry so @xyflow/svelte renders
 * the correct ArchiMate component instead of a text-only fallback.
 */

// These are the node types used in _build_enterprise_model() seed data
const ENTERPRISE_MODEL_NODE_TYPES = [
	'business_actor',
	'application_component',
	'application_service',
	'technology_node',
	'technology_service',
];

describe('ArchiMate seed data node types (ADR-054)', () => {
	it.each(ENTERPRISE_MODEL_NODE_TYPES)(
		'archimateNodeTypes registry contains "%s"',
		(nodeType) => {
			expect(archimateNodeTypes).toHaveProperty(nodeType);
		},
	);

	it('archimateNodeTypes registry has all 11 ArchiMate types', () => {
		expect(Object.keys(archimateNodeTypes)).toHaveLength(11);
	});

	it('all enterprise model types are a subset of the registry', () => {
		const registryTypes = Object.keys(archimateNodeTypes);
		for (const type of ENTERPRISE_MODEL_NODE_TYPES) {
			expect(registryTypes).toContain(type);
		}
	});
});
