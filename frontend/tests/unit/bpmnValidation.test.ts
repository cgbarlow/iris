import { describe, it, expect } from 'vitest';
import {
	validateBpmn,
	canConnect,
	type BpmnDiagramData,
	type BpmnNode,
} from '$lib/canvas/validation/bpmnRules';

const node = (id: string, type: string, parentId: string | null = null, label = ''): BpmnNode => ({
	id,
	type,
	parentId,
	data: { entityType: type, label },
});

const seq = (id: string, source: string, target: string) => ({
	id, source, target, type: 'sequence_flow',
});

describe('canConnect (draw-time prevention)', () => {
	it('blocks a sequence flow that crosses two pools', () => {
		const nodes = [
			node('p1', 'pool'),
			node('p2', 'pool'),
			node('t1', 'task', 'p1'),
			node('t2', 'task', 'p2'),
		];
		const v = canConnect({ source: nodes[2], target: nodes[3], edgeType: 'sequence_flow', nodes });
		expect(v.allowed).toBe(false);
		expect(v.ruleId).toBe('sequence_flow_crosses_pool');
		expect(v.reason).toMatch(/Message Flow/);
	});

	it('allows a sequence flow inside a single pool', () => {
		const nodes = [
			node('p1', 'pool'),
			node('t1', 'task', 'p1'),
			node('t2', 'task', 'p1'),
		];
		const v = canConnect({ source: nodes[1], target: nodes[2], edgeType: 'sequence_flow', nodes });
		expect(v.allowed).toBe(true);
	});

	it('blocks a message flow within a single pool', () => {
		const nodes = [
			node('p1', 'pool'),
			node('t1', 'task', 'p1'),
			node('t2', 'task', 'p1'),
		];
		const v = canConnect({ source: nodes[1], target: nodes[2], edgeType: 'message_flow', nodes });
		expect(v.allowed).toBe(false);
		expect(v.ruleId).toBe('message_flow_within_pool');
	});

	it('blocks an outgoing sequence flow from an end event', () => {
		const nodes = [node('e1', 'event_end'), node('t1', 'task')];
		const v = canConnect({ source: nodes[0], target: nodes[1], edgeType: 'sequence_flow', nodes });
		expect(v.allowed).toBe(false);
		expect(v.ruleId).toBe('outflow_from_end_event');
	});

	it('blocks an incoming sequence flow into a start event', () => {
		const nodes = [node('t1', 'task'), node('s1', 'event_start')];
		const v = canConnect({ source: nodes[0], target: nodes[1], edgeType: 'sequence_flow', nodes });
		expect(v.allowed).toBe(false);
		expect(v.ruleId).toBe('inflow_to_start_event');
	});
});

describe('validateBpmn (whole-diagram problems)', () => {
	const baseProcess: BpmnDiagramData = {
		nodes: [
			node('s1', 'event_start'),
			node('t1', 'task', null, 'Do Work'),
			node('e1', 'event_end'),
		],
		edges: [seq('seq1', 's1', 't1'), seq('seq2', 't1', 'e1')],
	};

	it('reports zero problems for a minimal well-formed process', () => {
		expect(validateBpmn(baseProcess)).toEqual([]);
	});

	it('warns when a process has no start event', () => {
		const data: BpmnDiagramData = { nodes: [node('t1', 'task')], edges: [] };
		const ids = validateBpmn(data).map(p => p.ruleId);
		expect(ids).toContain('missing_start_event');
	});

	it('warns when a process has no end event', () => {
		const data: BpmnDiagramData = { nodes: [node('s1', 'event_start'), node('t1', 'task')], edges: [seq('e1', 's1', 't1')] };
		const ids = validateBpmn(data).map(p => p.ruleId);
		expect(ids).toContain('missing_end_event');
	});

	it('reports orphan activities', () => {
		const data: BpmnDiagramData = {
			nodes: [node('t1', 'task', null, 'Orphan'), node('s1', 'event_start'), node('t2', 'task'), node('e1', 'event_end')],
			edges: [seq('e2', 's1', 't2'), seq('e3', 't2', 'e1')],
		};
		const ids = validateBpmn(data).map(p => p.ruleId);
		expect(ids).toContain('orphan_activity');
	});

	it('reports lanes that are not inside a pool', () => {
		const data: BpmnDiagramData = { nodes: [node('l1', 'lane')], edges: [] };
		const ids = validateBpmn(data).map(p => p.ruleId);
		expect(ids).toContain('lane_outside_pool');
	});

	it('reports a sequence flow that crosses two pools', () => {
		const data: BpmnDiagramData = {
			nodes: [
				node('p1', 'pool'),
				node('p2', 'pool'),
				node('t1', 'task', 'p1'),
				node('t2', 'task', 'p2'),
			],
			edges: [{ id: 'cross', source: 't1', target: 't2', type: 'sequence_flow' }],
		};
		const ids = validateBpmn(data).map(p => p.ruleId);
		expect(ids).toContain('sequence_flow_crosses_pool');
	});

	it('reports a message flow within a single pool', () => {
		const data: BpmnDiagramData = {
			nodes: [node('p1', 'pool'), node('t1', 'task', 'p1'), node('t2', 'task', 'p1')],
			edges: [{ id: 'msg', source: 't1', target: 't2', type: 'message_flow' }],
		};
		const ids = validateBpmn(data).map(p => p.ruleId);
		expect(ids).toContain('message_flow_within_pool');
	});

	it('reports a pointless gateway with 1 in and 1 out', () => {
		const data: BpmnDiagramData = {
			nodes: [
				node('s1', 'event_start'),
				node('g1', 'gateway'),
				node('t1', 'task'),
				node('e1', 'event_end'),
			],
			edges: [seq('a', 's1', 'g1'), seq('b', 'g1', 't1'), seq('c', 't1', 'e1')],
		};
		const ids = validateBpmn(data).map(p => p.ruleId);
		expect(ids).toContain('pointless_gateway');
	});

	it('reports unbalanced gateways (more diverging than converging)', () => {
		const data: BpmnDiagramData = {
			nodes: [
				node('s1', 'event_start'),
				node('g1', 'gateway'),
				node('t1', 'task'),
				node('t2', 'task'),
				node('e1', 'event_end'),
				node('e2', 'event_end'),
			],
			edges: [
				seq('a', 's1', 'g1'),
				seq('b', 'g1', 't1'),
				seq('c', 'g1', 't2'),
				seq('d', 't1', 'e1'),
				seq('e', 't2', 'e2'),
			],
		};
		const ids = validateBpmn(data).map(p => p.ruleId);
		expect(ids).toContain('unbalanced_gateways');
	});

	it('reports unlinked text annotations', () => {
		const data: BpmnDiagramData = {
			nodes: [
				node('s1', 'event_start'),
				node('t1', 'task'),
				node('e1', 'event_end'),
				node('a1', 'text_annotation', null, 'Note'),
			],
			edges: [seq('e2', 's1', 't1'), seq('e3', 't1', 'e1')],
		};
		const ids = validateBpmn(data).map(p => p.ruleId);
		expect(ids).toContain('text_annotation_unlinked');
	});
});
