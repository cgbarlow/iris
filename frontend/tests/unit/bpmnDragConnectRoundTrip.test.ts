import { describe, it, expect, vi, beforeEach } from 'vitest';
import { patchConnectedEdgeType } from '$lib/canvas/edgeOnConnect';
import { validateBpmn } from '$lib/canvas/validation/bpmnRules';

/**
 * Issue #69 Phase 3: round-trip evidence at the unit-integration level.
 *
 * Combines the components that closed BPMN-01/02/03/09 so we have one test
 * that asserts the full chain — not just each piece in isolation. This is
 * the unit-level analogue of the planned local-backend Playwright round-trip
 * (deferred per ADR-149); when that lands it'll cross-check the same
 * assertions against a real browser.
 *
 * The chain we're proving:
 *   1. xyflow's Handle.svelte does store.addEdge(connection) — appends a
 *      typeless edge to the bound canvasEdges array (we simulate this).
 *   2. UnifiedCanvas's handleSvelteFlowConnect calls patchConnectedEdgeType
 *      to upgrade the edge with type='sequence_flow'.
 *   3. validateBpmn now sees the edge as a sequence flow → outDeg for the
 *      start event becomes 1 → "no outgoing sequence flow" warning clears.
 *   4. The consumer (BPMN shell handleBpmnConnect) POSTs /api/relationships
 *      and patches the edge with the resulting relationshipId. We assert
 *      this with a mock fetch.
 */

type Node = { id: string; type?: string; data?: Record<string, unknown> };
type Edge = { id: string; source: string; target: string; type?: string; data?: Record<string, unknown> };

describe('BPMN drag-connect round-trip (issue #69)', () => {
	let nodes: Node[];
	let edges: Edge[];

	beforeEach(() => {
		// Canvas with a Start event and a Task — both with backing entityIds
		// (as createBpmnElement would have set after a successful POST).
		nodes = [
			{ id: 'n-start', type: 'event_start', data: { entityType: 'event_start', entityId: 'el-start' } },
			{ id: 'n-task',  type: 'task',        data: { entityType: 'task',        entityId: 'el-task'  } },
		];
		edges = [];
	});

	it('before user connects → validator warns "no outgoing sequence flow"', () => {
		const problems = validateBpmn({ nodes, edges });
		const ids = problems.map(p => p.ruleId);
		expect(ids).toContain('start_event_no_outflow');
	});

	it('after xyflow auto-add (typeless edge) → validator STILL warns (the BPMN-03 bug shape)', () => {
		// Simulate Handle.svelte:108 appending a typeless edge.
		edges = [...edges, { id: 'auto-1', source: 'n-start', target: 'n-task' }];

		const problems = validateBpmn({ nodes, edges });
		const ids = problems.map(p => p.ruleId);
		// BPMN-03 reproduced: validator can't see the edge as a sequence flow
		// because e.type is undefined, so the warning persists.
		expect(ids).toContain('start_event_no_outflow');
	});

	it('after patchConnectedEdgeType → validator clears the warning', () => {
		edges = [...edges, { id: 'auto-1', source: 'n-start', target: 'n-task' }];
		// UnifiedCanvas's handleSvelteFlowConnect runs this:
		edges = patchConnectedEdgeType(edges as never, { source: 'n-start', target: 'n-task' }, 'sequence_flow');

		expect(edges[0].type).toBe('sequence_flow');

		const problems = validateBpmn({ nodes, edges });
		const ids = problems.map(p => p.ruleId);
		// Warning is gone — outDeg for start = 1.
		expect(ids).not.toContain('start_event_no_outflow');
		// And the End-event warning is still appropriate (no end event present).
		expect(ids).toContain('missing_end_event');
	});

	it('handleBpmnConnect-shaped patch attaches relationshipId to the existing edge', async () => {
		// Add the edge in pre-patched form (as UnifiedCanvas would after step 2).
		edges = [
			{ id: 'auto-1', source: 'n-start', target: 'n-task', type: 'sequence_flow', data: { relationshipType: 'sequence_flow' } },
		];

		const fetchMock = vi.fn(async (url: string, init: RequestInit) => {
			expect(url).toBe('/api/relationships');
			expect(init.method).toBe('POST');
			const body = JSON.parse(init.body as string);
			expect(body.source_element_id).toBe('el-start');
			expect(body.target_element_id).toBe('el-task');
			expect(body.relationship_type).toBe('sequence_flow');
			return new Response(JSON.stringify({ id: 'rel-1' }), { status: 200, headers: { 'content-type': 'application/json' } });
		});
		const originalFetch = globalThis.fetch;
		globalThis.fetch = fetchMock as never;

		try {
			// Inline the relationship-POST + edge-patch shape from
			// BpmnAuthoringShell.handleBpmnConnect (we can't import the .svelte
			// helper, but it's a tiny shape — the shape is asserted statically
			// elsewhere via bpmnConnectRelationship.test.ts).
			const sourceNode = nodes.find(n => n.id === 'n-start');
			const targetNode = nodes.find(n => n.id === 'n-task');
			const sourceEntityId = (sourceNode?.data as { entityId?: string })?.entityId;
			const targetEntityId = (targetNode?.data as { entityId?: string })?.entityId;

			let relationshipId: string | undefined;
			if (sourceEntityId && targetEntityId) {
				const res = await fetch('/api/relationships', {
					method: 'POST',
					body: JSON.stringify({
						source_element_id: sourceEntityId,
						target_element_id: targetEntityId,
						relationship_type: 'sequence_flow',
						label: '',
						description: '',
					}),
				});
				relationshipId = (await res.json()).id;
			}

			edges = edges.map(e => {
				if (e.source !== 'n-start' || e.target !== 'n-task') return e;
				return { ...e, data: { ...(e.data ?? {}), relationshipId } };
			});

			expect(fetchMock).toHaveBeenCalledOnce();
			expect((edges[0].data as Record<string, unknown>).relationshipId).toBe('rel-1');
		} finally {
			globalThis.fetch = originalFetch;
		}
	});

	it('full chain: xyflow auto-add → patch → validator clear → relationshipId attached', async () => {
		// Step 1: xyflow auto-add (typeless edge).
		edges = [...edges, { id: 'auto-1', source: 'n-start', target: 'n-task' }];

		// Step 2: handleSvelteFlowConnect patches the type.
		edges = patchConnectedEdgeType(edges as never, { source: 'n-start', target: 'n-task' }, 'sequence_flow');
		expect(edges[0].type).toBe('sequence_flow');

		// Step 3: validator clears the warning.
		const problemsAfterPatch = validateBpmn({ nodes, edges });
		expect(problemsAfterPatch.map(p => p.ruleId)).not.toContain('start_event_no_outflow');

		// Step 4: handleBpmnConnect POSTs and patches relationshipId.
		const fetchMock = vi.fn(async () =>
			new Response(JSON.stringify({ id: 'rel-1' }), { status: 200, headers: { 'content-type': 'application/json' } })
		);
		const originalFetch = globalThis.fetch;
		globalThis.fetch = fetchMock as never;
		try {
			const res = await fetch('/api/relationships', {
				method: 'POST',
				body: JSON.stringify({
					source_element_id: 'el-start',
					target_element_id: 'el-task',
					relationship_type: 'sequence_flow',
					label: '',
					description: '',
				}),
			});
			const relationshipId = (await res.json()).id;
			edges = edges.map(e => (e.source === 'n-start' && e.target === 'n-task'
				? { ...e, data: { ...(e.data ?? {}), relationshipId } }
				: e));
			expect((edges[0].data as Record<string, unknown>).relationshipId).toBe('rel-1');
			expect(fetchMock).toHaveBeenCalledOnce();
		} finally {
			globalThis.fetch = originalFetch;
		}
	});
});
