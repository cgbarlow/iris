/**
 * BPMN 2.0 validation rules (ADR-136, ADR-082).
 *
 * Pure functions over diagram canvas data. Consumed by:
 *  - draw-time prevention (canConnect) — silent block + toast
 *  - persistent ProblemsPanel (validate) — list of warnings with click-to-focus
 *
 * Rules cover the 15 most common BPMN anti-patterns from the literature
 * (Pavlicek 2019; Modern Analyst BPMN best-practices). They're rigorous
 * enough to be useful but not so strict that pragmatic models get rejected.
 */

export interface BpmnNode {
	id: string;
	type?: string;          // entityType when stored on the node (Svelte Flow)
	parentId?: string | null;
	data?: Record<string, unknown>;
}

export interface BpmnEdge {
	id: string;
	source: string;
	target: string;
	type?: string;          // relationshipType
	data?: Record<string, unknown>;
}

export interface BpmnDiagramData {
	nodes: BpmnNode[];
	edges: BpmnEdge[];
}

export type Severity = 'error' | 'warning' | 'info';

export interface BpmnProblem {
	ruleId: string;
	severity: Severity;
	message: string;
	/** Element IDs the problem refers to — used to focus the canvas on click. */
	elementIds: string[];
}

/* ── Helpers ──────────────────────────────────────────────────────────────── */

const ENTITY = (n: BpmnNode): string => n.type ?? (n.data?.entityType as string) ?? '';

const isEvent       = (n: BpmnNode) => ENTITY(n).startsWith('event_');
const isStart       = (n: BpmnNode) => ENTITY(n) === 'event_start';
const isEnd         = (n: BpmnNode) => ENTITY(n) === 'event_end';
const isGateway     = (n: BpmnNode) => ENTITY(n) === 'gateway';
const isPool        = (n: BpmnNode) => ENTITY(n) === 'pool';
const isLane        = (n: BpmnNode) => ENTITY(n) === 'lane';
const isActivity    = (n: BpmnNode) => ['task', 'subprocess', 'call_activity'].includes(ENTITY(n));
const isSequence    = (e: BpmnEdge) => (e.type ?? (e.data?.relationshipType as string) ?? '').startsWith('sequence_flow');
const isMessageFlow = (e: BpmnEdge) => (e.type ?? (e.data?.relationshipType as string) ?? '') === 'message_flow';

/** Walk parent chain to find the enclosing pool, if any. */
function findPool(node: BpmnNode | undefined, byId: Map<string, BpmnNode>): BpmnNode | null {
	let cur = node;
	const seen = new Set<string>();
	while (cur && cur.parentId && !seen.has(cur.parentId)) {
		seen.add(cur.parentId);
		const parent = byId.get(cur.parentId);
		if (!parent) return null;
		if (isPool(parent)) return parent;
		cur = parent;
	}
	return null;
}

/* ── Connection-time check (returns true if connection allowed) ──────────── */

export interface ConnectAttempt {
	source: BpmnNode;
	target: BpmnNode;
	edgeType: string;
	nodes: BpmnNode[];
}

export interface ConnectVerdict {
	allowed: boolean;
	reason?: string;     // 1-line toast text for blocked connections
	ruleId?: string;
}

export function canConnect({ source, target, edgeType, nodes }: ConnectAttempt): ConnectVerdict {
	const byId = new Map(nodes.map(n => [n.id, n]));
	const sourcePool = findPool(source, byId);
	const targetPool = findPool(target, byId);

	if (edgeType.startsWith('sequence_flow')) {
		if (sourcePool && targetPool && sourcePool.id !== targetPool.id) {
			return {
				allowed: false,
				ruleId: 'sequence_flow_crosses_pool',
				reason: "Sequence flows can't cross pools — use a Message Flow instead.",
			};
		}
		if (isEnd(source)) {
			return { allowed: false, ruleId: 'outflow_from_end_event', reason: 'End events cannot have outgoing sequence flows.' };
		}
		if (isStart(target)) {
			return { allowed: false, ruleId: 'inflow_to_start_event', reason: 'Start events cannot have incoming sequence flows.' };
		}
	}

	if (edgeType === 'message_flow') {
		if (sourcePool && targetPool && sourcePool.id === targetPool.id) {
			return {
				allowed: false,
				ruleId: 'message_flow_within_pool',
				reason: 'Message flows must cross pools — use a Sequence Flow within a single pool.',
			};
		}
	}

	return { allowed: true };
}

/* ── Whole-diagram validation (returns 0..N problems) ────────────────────── */

export function validateBpmn(data: BpmnDiagramData): BpmnProblem[] {
	const problems: BpmnProblem[] = [];
	const byId = new Map(data.nodes.map(n => [n.id, n]));

	const inDeg = new Map<string, number>();
	const outDeg = new Map<string, number>();
	for (const e of data.edges) {
		if (!isSequence(e) && !isMessageFlow(e)) continue;
		outDeg.set(e.source, (outDeg.get(e.source) ?? 0) + 1);
		inDeg.set(e.target, (inDeg.get(e.target) ?? 0) + 1);
	}

	const allEvents = data.nodes.filter(isEvent);
	const hasStart = allEvents.some(isStart);
	const hasEnd = allEvents.some(isEnd);

	// Rule 1: every process must have at least one start event.
	if (!hasStart && data.nodes.some(isActivity)) {
		problems.push({
			ruleId: 'missing_start_event',
			severity: 'warning',
			message: 'No Start Event — processes should begin with a Start Event.',
			elementIds: [],
		});
	}

	// Rule 2: every process must have at least one end event.
	if (!hasEnd && data.nodes.some(isActivity)) {
		problems.push({
			ruleId: 'missing_end_event',
			severity: 'warning',
			message: 'No End Event — processes should end with at least one End Event.',
			elementIds: [],
		});
	}

	for (const n of data.nodes) {
		// Rule 3: start events must not have incoming sequence flows.
		if (isStart(n) && (inDeg.get(n.id) ?? 0) > 0) {
			problems.push({
				ruleId: 'start_event_has_inflow',
				severity: 'error',
				message: 'Start Event has incoming sequence flow.',
				elementIds: [n.id],
			});
		}
		// Rule 4: end events must not have outgoing sequence flows.
		if (isEnd(n) && (outDeg.get(n.id) ?? 0) > 0) {
			problems.push({
				ruleId: 'end_event_has_outflow',
				severity: 'error',
				message: 'End Event has outgoing sequence flow.',
				elementIds: [n.id],
			});
		}
		// Rule 5: start events should have exactly one outgoing sequence flow.
		if (isStart(n) && (outDeg.get(n.id) ?? 0) === 0) {
			problems.push({
				ruleId: 'start_event_no_outflow',
				severity: 'warning',
				message: 'Start Event has no outgoing sequence flow.',
				elementIds: [n.id],
			});
		}
		// Rule 6: end events should have exactly one incoming sequence flow.
		if (isEnd(n) && (inDeg.get(n.id) ?? 0) === 0) {
			problems.push({
				ruleId: 'end_event_no_inflow',
				severity: 'warning',
				message: 'End Event has no incoming sequence flow.',
				elementIds: [n.id],
			});
		}
		// Rule 7: activities should be connected (have at least one in or out).
		if (isActivity(n) && (inDeg.get(n.id) ?? 0) === 0 && (outDeg.get(n.id) ?? 0) === 0) {
			problems.push({
				ruleId: 'orphan_activity',
				severity: 'warning',
				message: `Activity "${(n.data?.label as string) ?? n.id}" has no connections.`,
				elementIds: [n.id],
			});
		}
		// Rule 8: lanes must be inside pools.
		if (isLane(n)) {
			const pool = findPool(n, byId);
			if (!pool) {
				problems.push({
					ruleId: 'lane_outside_pool',
					severity: 'error',
					message: 'Lane is not inside a Pool.',
					elementIds: [n.id],
				});
			}
		}
		// Rule 9: gateways with one in + one out are pointless.
		if (isGateway(n) && (inDeg.get(n.id) ?? 0) === 1 && (outDeg.get(n.id) ?? 0) === 1) {
			problems.push({
				ruleId: 'pointless_gateway',
				severity: 'info',
				message: 'Gateway has only 1 incoming and 1 outgoing flow — usually redundant.',
				elementIds: [n.id],
			});
		}
	}

	for (const e of data.edges) {
		const source = byId.get(e.source);
		const target = byId.get(e.target);
		if (!source || !target) continue;

		if (isSequence(e)) {
			const sp = findPool(source, byId);
			const tp = findPool(target, byId);
			// Rule 10: sequence flows must not cross pools.
			if (sp && tp && sp.id !== tp.id) {
				problems.push({
					ruleId: 'sequence_flow_crosses_pool',
					severity: 'error',
					message: 'Sequence flow crosses pools — use a Message Flow.',
					elementIds: [e.id, e.source, e.target],
				});
			}
		}

		if (isMessageFlow(e)) {
			const sp = findPool(source, byId);
			const tp = findPool(target, byId);
			// Rule 11: message flows must cross pools.
			if (sp && tp && sp.id === tp.id) {
				problems.push({
					ruleId: 'message_flow_within_pool',
					severity: 'error',
					message: 'Message flow within a single pool — use a Sequence Flow.',
					elementIds: [e.id, e.source, e.target],
				});
			}
			// Rule 12: message flows source/target must be activities, events, or pools.
			const validKinds = new Set(['task', 'subprocess', 'call_activity', 'event_start', 'event_intermediate', 'event_end', 'event_boundary', 'pool']);
			if (!validKinds.has(ENTITY(source)) || !validKinds.has(ENTITY(target))) {
				problems.push({
					ruleId: 'message_flow_invalid_endpoint',
					severity: 'warning',
					message: 'Message flow endpoints should be activities, events, or pools.',
					elementIds: [e.id],
				});
			}
		}
	}

	// Rule 13: only one Start event per process is recommended.
	const starts = data.nodes.filter(isStart);
	if (starts.length > 1) {
		problems.push({
			ruleId: 'multiple_start_events',
			severity: 'info',
			message: `Multiple Start Events (${starts.length}) — consider whether each represents a distinct trigger.`,
			elementIds: starts.map(s => s.id),
		});
	}

	// Rule 14: gateways should converge what they diverge.
	const diverging = data.nodes.filter(n => isGateway(n) && (outDeg.get(n.id) ?? 0) > 1);
	const converging = data.nodes.filter(n => isGateway(n) && (inDeg.get(n.id) ?? 0) > 1);
	if (diverging.length > converging.length) {
		problems.push({
			ruleId: 'unbalanced_gateways',
			severity: 'info',
			message: `${diverging.length} diverging gateway(s) but only ${converging.length} converging — branches may not merge.`,
			elementIds: diverging.map(g => g.id),
		});
	}

	// Rule 15: text annotations should be linked via Association.
	for (const n of data.nodes) {
		if (ENTITY(n) === 'text_annotation') {
			const linked = data.edges.some(e =>
				(e.type ?? e.data?.relationshipType) === 'association' &&
				(e.source === n.id || e.target === n.id),
			);
			if (!linked) {
				problems.push({
					ruleId: 'text_annotation_unlinked',
					severity: 'info',
					message: 'Text Annotation is not attached to anything via an Association.',
					elementIds: [n.id],
				});
			}
		}
	}

	return problems;
}
