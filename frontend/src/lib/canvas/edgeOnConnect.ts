/**
 * Issue #69 / BPMN-03 root cause fix.
 *
 * xyflow svelte's `Handle.svelte` runs `store.addEdge(connection)` immediately
 * after `isValidConnection` returns true (Handle.svelte:108). The `addEdge`
 * util in `@xyflow/system` (index.mjs:1048) does
 * `edges.concat({ ...edgeParams, id: getEdgeId(...) })` — it does NOT apply
 * `defaultEdgeOptions`. The Connection object only carries
 * `{source, target, sourceHandle, targetHandle}`, so the auto-added edge has
 * **no `type` field**.
 *
 * Downstream code (validators, persistence, edge renderer) keys on `e.type`,
 * and a missing type means "no outgoing sequence flow" warnings persist after
 * the user has visually connected nodes — the user-facing repro for issue #69.
 *
 * `patchConnectedEdgeType` is the pure helper called from `<SvelteFlow>`'s
 * `onconnect` to upgrade the auto-added edge with the right type. Idempotent:
 * already-typed edges are returned untouched.
 */
import type { Connection } from '@xyflow/svelte';
import type { CanvasEdge } from '$lib/types/canvas';

export function patchConnectedEdgeType(
	edges: CanvasEdge[],
	connection: Pick<Connection, 'source' | 'target'>,
	defaultEdgeType: string,
): CanvasEdge[] {
	if (!connection.source || !connection.target) return edges;
	const isSelfLoop = connection.source === connection.target;
	const wantedType = isSelfLoop ? 'self_loop' : defaultEdgeType;
	return edges.map((e) => {
		if (e.source !== connection.source || e.target !== connection.target) return e;
		if (e.type) return e;
		const data = { ...((e as { data?: Record<string, unknown> }).data ?? {}), relationshipType: wantedType };
		return { ...e, type: wantedType, data } as CanvasEdge;
	});
}
