/**
 * Tests for the shared elementToNodeData() helper (ADR-192, issue #164).
 *
 * Backstory: canvas nodes were minted with only label/entityType/
 * description/entityId/notation. Class element attributes / operations /
 * literals lived on the backend ``element.data`` JSON but never made
 * it onto the node — so a class element whose attributes were edited
 * via the element-detail page showed empty compartments on diagrams.
 *
 * The helper is the single source of truth for "given a backend
 * Element, produce the canvas node ``data`` payload". Used by
 * handleAddElement, handleLinkElement, and refreshNodeDescriptions
 * on /views/[id]/+page.svelte.
 */
import { describe, it, expect } from 'vitest';
import { elementToNodeData } from '$lib/canvas/elementToNodeData';
import type { Element } from '$lib/types/api';

const base: Element = {
	id: 'el-1',
	element_type: 'class',
	current_version: 1,
	name: 'Order',
	description: 'An order placed by a customer.',
	data: {},
	created_at: '2026-05-17T00:00:00Z',
	created_by: 'u1',
	updated_at: '2026-05-17T00:00:00Z',
	is_deleted: false,
};

describe('elementToNodeData', () => {
	it('carries label, entityType, entityId, description, notation from the element', () => {
		const node = elementToNodeData({ ...base, notation: 'uml' });
		expect(node.label).toBe('Order');
		expect(node.entityType).toBe('class');
		expect(node.entityId).toBe('el-1');
		expect(node.description).toBe('An order placed by a customer.');
		expect(node.notation).toBe('uml');
	});

	it('coerces missing description to empty string', () => {
		const node = elementToNodeData({ ...base, description: null });
		expect(node.description).toBe('');
	});

	it('defaults notation to "simple" when the element does not set one', () => {
		const node = elementToNodeData({ ...base, notation: undefined });
		expect(node.notation).toBe('simple');
	});

	it('hydrates class attributes from element.data.attributes', () => {
		const attributes = [
			{ name: 'id', type: 'string', scope: 'Private' as const },
			{ name: 'total', type: 'number' },
		];
		const node = elementToNodeData({ ...base, data: { attributes } });
		expect(node.attributes).toEqual(attributes);
	});

	it('hydrates operations + literals + stereotype + qualifier from element.data', () => {
		const node = elementToNodeData({
			...base,
			data: {
				operations: ['ship()', 'cancel()'],
				literals: ['ACTIVE', 'CLOSED'],
				stereotype: 'entity',
				qualifier: 'inventory',
			},
		});
		expect(node.operations).toEqual(['ship()', 'cancel()']);
		expect(node.literals).toEqual(['ACTIVE', 'CLOSED']);
		expect(node.stereotype).toBe('entity');
		expect(node.qualifier).toBe('inventory');
	});

	it('passes through visual overrides on element.data.visual', () => {
		const visual = { width: 300, height: 120, icon: 'box' };
		const node = elementToNodeData({ ...base, data: { visual } });
		expect(node.visual).toEqual(visual);
	});

	it('handles an element with no data field (treats as empty)', () => {
		const node = elementToNodeData({ ...base, data: undefined as unknown as Record<string, unknown> });
		expect(node.attributes).toBeUndefined();
		expect(node.operations).toBeUndefined();
		expect(node.label).toBe('Order');
	});

	it('reads diagramUsageCount from the element', () => {
		const node = elementToNodeData({ ...base, diagram_usage_count: 7 });
		expect(node.diagramUsageCount).toBe(7);
	});

	it('defaults diagramUsageCount to 0 when not provided', () => {
		const node = elementToNodeData(base);
		expect(node.diagramUsageCount).toBe(0);
	});
});
