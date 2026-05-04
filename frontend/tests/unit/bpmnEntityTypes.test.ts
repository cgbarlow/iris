import { describe, it, expect } from 'vitest';
import {
	BPMN_ENTITY_TYPES,
	BPMN_RELATIONSHIP_TYPES,
	BPMN_DIAGRAM_TYPE_FILTER,
	BPMN_DEFAULT_DISCRIMINATORS,
	type BpmnCategory,
	type BpmnEntityType,
} from '$lib/types/canvas';

describe('BPMN entity catalogue (ADR-136)', () => {
	it('declares 14 base entity types covering every BPMN category', () => {
		const keys = BPMN_ENTITY_TYPES.map(e => e.key).sort();
		expect(keys).toEqual([
			'call_activity',
			'data_object',
			'data_store',
			'event_boundary',
			'event_end',
			'event_intermediate',
			'event_start',
			'gateway',
			'group',
			'lane',
			'pool',
			'subprocess',
			'task',
			'text_annotation',
		]);
	});

	it('groups entries into the six BPMN 2.0 §7.4 categories', () => {
		const categories = new Set<BpmnCategory>(BPMN_ENTITY_TYPES.map(e => e.category));
		expect(categories).toEqual(new Set(['activity', 'event', 'gateway', 'swimlane', 'data', 'artifact']));
	});

	it('provides a label, icon, and description for every entry', () => {
		for (const e of BPMN_ENTITY_TYPES) {
			expect(e.label.length).toBeGreaterThan(0);
			expect(e.icon.length).toBeGreaterThan(0);
			expect(e.description.length).toBeGreaterThan(0);
		}
	});

	it('event entries describe the trigger discriminator in their description', () => {
		const events = BPMN_ENTITY_TYPES.filter(e => e.category === 'event');
		for (const e of events) {
			expect(e.description.toLowerCase()).toContain('eventtrigger');
		}
	});
});

describe('BPMN relationship catalogue', () => {
	it('declares the six BPMN connecting object types', () => {
		const keys = BPMN_RELATIONSHIP_TYPES.map(r => r.key).sort();
		expect(keys).toEqual([
			'association',
			'data_association',
			'message_flow',
			'sequence_flow',
			'sequence_flow_conditional',
			'sequence_flow_default',
		]);
	});
});

describe('BPMN diagram-type filtering (ADR-082)', () => {
	it('process diagrams disallow pool (single-pool implicit)', () => {
		expect(BPMN_DIAGRAM_TYPE_FILTER.process).toBeDefined();
		expect(BPMN_DIAGRAM_TYPE_FILTER.process).not.toContain('pool');
	});

	it('collaboration permits every BPMN element', () => {
		expect(BPMN_DIAGRAM_TYPE_FILTER.collaboration).toBeNull();
	});

	it('choreography excludes pools/lanes/data/artifacts', () => {
		const allowed = BPMN_DIAGRAM_TYPE_FILTER.choreography ?? [];
		expect(allowed).not.toContain('pool');
		expect(allowed).not.toContain('lane');
		expect(allowed).not.toContain('data_object');
	});

	it('free_form removes every restriction', () => {
		expect(BPMN_DIAGRAM_TYPE_FILTER.free_form).toBeNull();
	});
});

describe('BPMN default discriminators', () => {
	it('provides a default discriminator preset for every entity type', () => {
		for (const e of BPMN_ENTITY_TYPES) {
			expect(BPMN_DEFAULT_DISCRIMINATORS[e.key as BpmnEntityType]).toBeDefined();
		}
	});

	it('task defaults to taskType=none, gateway to exclusive, event_boundary interrupts', () => {
		expect(BPMN_DEFAULT_DISCRIMINATORS.task.taskType).toBe('none');
		expect(BPMN_DEFAULT_DISCRIMINATORS.gateway.gatewayType).toBe('exclusive');
		expect(BPMN_DEFAULT_DISCRIMINATORS.event_boundary.boundaryInterrupting).toBe(true);
	});
});
