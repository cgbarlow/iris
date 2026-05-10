// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { patchConnectedEdgeType } from '$lib/canvas/edgeOnConnect';

/**
 * Issue #69 / BPMN-03 root cause:
 *
 * xyflow svelte's Handle.svelte calls `store.addEdge(connection)` immediately
 * after `isValidConnection` returns true. The `addEdge` util in @xyflow/system
 * (index.mjs:1048) does `edges.concat({ ...edgeParams, id: getEdgeId(...) })`
 * — it does NOT apply `defaultEdgeOptions`. The Connection object only has
 * `{source, target, sourceHandle, targetHandle}`, so the edge that ends up in
 * the bound `canvasEdges` array has **no `type` field**.
 *
 * Then `validateBpmn`'s `isSequence(e)` keys on `e.type === 'sequence_flow'`
 * — the type-less edge fails the check, `outDeg` doesn't get incremented for
 * the start event, and the "no outgoing sequence flow" warning persists even
 * though the user has visually drawn the edge.
 *
 * `patchConnectedEdgeType` is the pure helper that, called from SvelteFlow's
 * `onconnect`, upgrades the just-added edge with the right type so the
 * validator and downstream code see it correctly.
 */

describe('patchConnectedEdgeType — closes BPMN-03 / issue #69 root cause', () => {
	const conn = (s: string, t: string) => ({ source: s, target: t, sourceHandle: null, targetHandle: null });

	it('upgrades the just-added type-less edge to defaultEdgeType', () => {
		const edges = [{ id: 'auto-1', source: 'a', target: 'b' } as any];
		const result = patchConnectedEdgeType(edges, conn('a', 'b'), 'sequence_flow');
		expect(result[0].type).toBe('sequence_flow');
		expect(result[0].data?.relationshipType).toBe('sequence_flow');
	});

	it('preserves an existing edge id (matches the auto-added one in place)', () => {
		const edges = [{ id: 'auto-xy-1', source: 'a', target: 'b' } as any];
		const result = patchConnectedEdgeType(edges, conn('a', 'b'), 'sequence_flow');
		expect(result[0].id).toBe('auto-xy-1');
	});

	it('uses self_loop type when source === target', () => {
		const edges = [{ id: 'auto-2', source: 'x', target: 'x' } as any];
		const result = patchConnectedEdgeType(edges, conn('x', 'x'), 'sequence_flow');
		expect(result[0].type).toBe('self_loop');
	});

	it('is idempotent — does not re-patch an already-typed edge', () => {
		const edges = [
			{ id: 'e-1', source: 'a', target: 'b', type: 'sequence_flow', data: { label: 'keep' } } as any,
		];
		const result = patchConnectedEdgeType(edges, conn('a', 'b'), 'sequence_flow');
		expect(result[0]).toEqual(edges[0]);
	});

	it('only patches the matching edge, leaves siblings untouched', () => {
		const edges = [
			{ id: 'e-1', source: 'a', target: 'b', type: 'sequence_flow' } as any,
			{ id: 'auto-2', source: 'b', target: 'c' } as any,
			{ id: 'e-3', source: 'c', target: 'd', type: 'sequence_flow' } as any,
		];
		const result = patchConnectedEdgeType(edges, conn('b', 'c'), 'sequence_flow');
		expect(result[0]).toEqual(edges[0]);
		expect(result[1].type).toBe('sequence_flow');
		expect(result[2]).toEqual(edges[2]);
	});

	it('returns input unchanged for invalid connections (missing source or target)', () => {
		const edges = [{ id: 'auto-1', source: 'a', target: 'b' } as any];
		expect(patchConnectedEdgeType(edges, { source: null, target: 'b' } as any, 'sequence_flow')).toBe(edges);
		expect(patchConnectedEdgeType(edges, { source: 'a', target: null } as any, 'sequence_flow')).toBe(edges);
	});

	it('preserves existing data fields and merges relationshipType', () => {
		const edges = [
			{ id: 'auto-1', source: 'a', target: 'b', data: { sourceHandle: 'right' } } as any,
		];
		const result = patchConnectedEdgeType(edges, conn('a', 'b'), 'sequence_flow');
		expect(result[0].data?.sourceHandle).toBe('right');
		expect(result[0].data?.relationshipType).toBe('sequence_flow');
	});

	it('threads non-BPMN defaultEdgeType through unchanged (UML association, ArchiMate serving)', () => {
		const edges = [{ id: 'auto-1', source: 'a', target: 'b' } as any];
		expect(patchConnectedEdgeType(edges, conn('a', 'b'), 'association')[0].type).toBe('association');
		expect(patchConnectedEdgeType(edges, conn('a', 'b'), 'serving')[0].type).toBe('serving');
		expect(patchConnectedEdgeType(edges, conn('a', 'b'), 'uses')[0].type).toBe('uses');
	});
});
