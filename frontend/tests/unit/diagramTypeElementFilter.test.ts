import { describe, it, expect } from 'vitest';
import {
	SIMPLE_DIAGRAM_TYPE_FILTER,
	UML_DIAGRAM_TYPE_FILTER,
	ARCHIMATE_DIAGRAM_TYPE_LAYERS,
	C4_DIAGRAM_TYPE_LEVELS,
	SIMPLE_ENTITY_TYPES,
	UML_ENTITY_TYPES,
	ARCHIMATE_ENTITY_TYPES,
	C4_ENTITY_TYPES,
} from '$lib/types/canvas';

describe('Simple diagram-type element filtering (ADR-082)', () => {
	it('roadmap only allows component and service (plus universal note/boundary)', () => {
		const allowed = SIMPLE_DIAGRAM_TYPE_FILTER['roadmap'];
		expect(allowed).not.toBeNull();
		expect(allowed!.sort()).toEqual(['component', 'service']);
		// When applied, note and boundary are always kept as universal types
		const filtered = SIMPLE_ENTITY_TYPES.filter(
			(t) => allowed!.includes(t.key) || t.key === 'note' || t.key === 'boundary'
		);
		const keys = filtered.map((t) => t.key).sort();
		expect(keys).toEqual(['boundary', 'component', 'note', 'service']);
	});

	it('component diagram allows all 5 domain types', () => {
		const allowed = SIMPLE_DIAGRAM_TYPE_FILTER['component'];
		expect(allowed).not.toBeNull();
		expect(allowed!.sort()).toEqual(['actor', 'component', 'database', 'interface', 'service']);
	});

	it('sequence diagram allows component/service/actor', () => {
		const allowed = SIMPLE_DIAGRAM_TYPE_FILTER['sequence'];
		expect(allowed).not.toBeNull();
		expect(allowed!.sort()).toEqual(['actor', 'component', 'service']);
	});

	it('deployment diagram allows component/service/database', () => {
		const allowed = SIMPLE_DIAGRAM_TYPE_FILTER['deployment'];
		expect(allowed).not.toBeNull();
		expect(allowed!.sort()).toEqual(['component', 'database', 'service']);
	});

	it('process diagram allows component/service/actor', () => {
		const allowed = SIMPLE_DIAGRAM_TYPE_FILTER['process'];
		expect(allowed).not.toBeNull();
		expect(allowed!.sort()).toEqual(['actor', 'component', 'service']);
	});

	it('free_form returns null (no filter)', () => {
		expect(SIMPLE_DIAGRAM_TYPE_FILTER['free_form']).toBeNull();
	});

	it('every diagram type key has an entry in the filter map', () => {
		const expectedTypes = [
			'component', 'sequence', 'deployment', 'process', 'roadmap',
			'use_case', 'state_machine', 'system_context', 'container', 'free_form',
		];
		for (const dt of expectedTypes) {
			expect(SIMPLE_DIAGRAM_TYPE_FILTER).toHaveProperty(dt);
		}
	});
});

describe('UML diagram-type element filtering (ADR-082)', () => {
	it('class diagram only shows class/object/interface_uml/enumeration/abstract_class/package_uml', () => {
		const allowed = UML_DIAGRAM_TYPE_FILTER['class'];
		expect(allowed).not.toBeNull();
		expect(allowed!.sort()).toEqual(
			['class', 'object', 'interface_uml', 'enumeration', 'abstract_class', 'package_uml'].sort()
		);
	});

	it('component diagram only shows component_uml/interface_uml/package_uml/node', () => {
		const allowed = UML_DIAGRAM_TYPE_FILTER['component'];
		expect(allowed).not.toBeNull();
		expect(allowed!.sort()).toEqual(
			['component_uml', 'interface_uml', 'package_uml', 'node'].sort()
		);
	});

	it('use_case diagram shows use_case/component_uml/package_uml', () => {
		const allowed = UML_DIAGRAM_TYPE_FILTER['use_case'];
		expect(allowed).not.toBeNull();
		expect(allowed!.sort()).toEqual(['use_case', 'component_uml', 'package_uml'].sort());
	});

	it('state_machine diagram only shows state', () => {
		const allowed = UML_DIAGRAM_TYPE_FILTER['state_machine'];
		expect(allowed).not.toBeNull();
		expect(allowed).toEqual(['state']);
	});

	it('free_form returns null (no filter)', () => {
		expect(UML_DIAGRAM_TYPE_FILTER['free_form']).toBeNull();
	});

	it('filtering UML types by class diagram produces correct subset', () => {
		const allowed = UML_DIAGRAM_TYPE_FILTER['class']!;
		const filtered = UML_ENTITY_TYPES.filter((t) => allowed.includes(t.key));
		expect(filtered.length).toBe(6);
		const keys = filtered.map((t) => t.key).sort();
		expect(keys).toEqual(
			['abstract_class', 'class', 'enumeration', 'interface_uml', 'object', 'package_uml']
		);
	});
});

describe('ArchiMate diagram-type layer filtering (ADR-082)', () => {
	it('deployment diagram restricts to technology layer', () => {
		const allowed = ARCHIMATE_DIAGRAM_TYPE_LAYERS['deployment'];
		expect(allowed).not.toBeNull();
		expect(allowed).toEqual(['technology']);
	});

	it('motivation diagram restricts to motivation layer', () => {
		const allowed = ARCHIMATE_DIAGRAM_TYPE_LAYERS['motivation'];
		expect(allowed).not.toBeNull();
		expect(allowed).toEqual(['motivation']);
	});

	it('strategy diagram restricts to strategy layer', () => {
		const allowed = ARCHIMATE_DIAGRAM_TYPE_LAYERS['strategy'];
		expect(allowed).not.toBeNull();
		expect(allowed).toEqual(['strategy']);
	});

	it('component diagram allows application/technology/business layers', () => {
		const allowed = ARCHIMATE_DIAGRAM_TYPE_LAYERS['component'];
		expect(allowed).not.toBeNull();
		expect(allowed!.sort()).toEqual(['application', 'business', 'technology']);
	});

	it('free_form returns null (no filter)', () => {
		expect(ARCHIMATE_DIAGRAM_TYPE_LAYERS['free_form']).toBeNull();
	});

	it('filtering ArchiMate by motivation layer produces correct types', () => {
		const allowed = ARCHIMATE_DIAGRAM_TYPE_LAYERS['motivation']!;
		const filtered = ARCHIMATE_ENTITY_TYPES.filter((t) => allowed.includes(t.layer));
		expect(filtered.length).toBe(8);
		filtered.forEach((t) => expect(t.layer).toBe('motivation'));
	});
});

describe('C4 diagram-type level filtering (ADR-082)', () => {
	it('system_context diagram restricts to system_context level', () => {
		const allowed = C4_DIAGRAM_TYPE_LEVELS['system_context'];
		expect(allowed).not.toBeNull();
		expect(allowed).toEqual(['system_context']);
	});

	it('container diagram allows system_context + container levels', () => {
		const allowed = C4_DIAGRAM_TYPE_LEVELS['container'];
		expect(allowed).not.toBeNull();
		expect(allowed!.sort()).toEqual(['container', 'system_context']);
	});

	it('component diagram allows container + component levels', () => {
		const allowed = C4_DIAGRAM_TYPE_LEVELS['component'];
		expect(allowed).not.toBeNull();
		expect(allowed!.sort()).toEqual(['component', 'container']);
	});

	it('deployment diagram restricts to deployment level', () => {
		const allowed = C4_DIAGRAM_TYPE_LEVELS['deployment'];
		expect(allowed).not.toBeNull();
		expect(allowed).toEqual(['deployment']);
	});

	it('free_form returns null (no filter)', () => {
		expect(C4_DIAGRAM_TYPE_LEVELS['free_form']).toBeNull();
	});

	it('filtering C4 by system_context level produces person/software_system/software_system_external', () => {
		const allowed = C4_DIAGRAM_TYPE_LEVELS['system_context']!;
		const filtered = C4_ENTITY_TYPES.filter((t) => allowed.includes(t.level));
		expect(filtered.length).toBe(3);
		const keys = filtered.map((t) => t.key).sort();
		expect(keys).toEqual(['person', 'software_system', 'software_system_external']);
	});
});

describe('Override toggle behaviour (ADR-082)', () => {
	it('null filter value means show all types regardless of diagram type', () => {
		expect(UML_DIAGRAM_TYPE_FILTER['free_form']).toBeNull();
		expect(ARCHIMATE_DIAGRAM_TYPE_LAYERS['free_form']).toBeNull();
		expect(C4_DIAGRAM_TYPE_LEVELS['free_form']).toBeNull();
		expect(SIMPLE_DIAGRAM_TYPE_FILTER['free_form']).toBeNull();
	});

	it('all 4 filter maps have free_form as null', () => {
		// When showAllTypes is true, filtering is bypassed — equivalent to null
		expect(SIMPLE_DIAGRAM_TYPE_FILTER['free_form']).toBeNull();
		expect(UML_DIAGRAM_TYPE_FILTER['free_form']).toBeNull();
		expect(ARCHIMATE_DIAGRAM_TYPE_LAYERS['free_form']).toBeNull();
		expect(C4_DIAGRAM_TYPE_LEVELS['free_form']).toBeNull();
	});

	it('simple roadmap filter excludes actor/database/interface but override would restore them', () => {
		const allowed = SIMPLE_DIAGRAM_TYPE_FILTER['roadmap']!;
		// Without override: only component, service (+ note, boundary as universal)
		const filtered = SIMPLE_ENTITY_TYPES.filter(
			(t) => allowed.includes(t.key) || t.key === 'note' || t.key === 'boundary'
		);
		expect(filtered.length).toBe(4);
		// With override (null bypass): all 7 types available
		expect(SIMPLE_ENTITY_TYPES.length).toBe(7);
	});
});
