/**
 * Unified node/edge type registry for Svelte Flow.
 * Maps ALL type keys to DynamicNode/DynamicEdge.
 * The actual rendering is determined by notation context, not the registry.
 */

import type { Component } from 'svelte';
import DynamicNode from './DynamicNode.svelte';
import DynamicEdge from './DynamicEdge.svelte';

/** All node type keys across all notations. */
const ALL_NODE_TYPE_KEYS = [
	// Simple view
	'component', 'service', 'interface', 'package', 'actor', 'database', 'queue',
	// Universal
	'note', 'boundary', 'modelref',
	// UML
	'class', 'object', 'use_case', 'state', 'activity', 'node',
	'interface_uml', 'enumeration', 'abstract_class', 'component_uml', 'package_uml',
	// ArchiMate — Business
	'business_actor', 'business_role', 'business_process', 'business_service',
	'business_object', 'business_function', 'business_interaction', 'business_event',
	'business_collaboration', 'business_interface',
	// ArchiMate — Application
	'application_component', 'application_service', 'application_interface',
	'application_function', 'application_interaction', 'application_event',
	'application_collaboration', 'application_process',
	// ArchiMate — Technology
	'technology_node', 'technology_service', 'technology_interface',
	'technology_function', 'technology_interaction', 'technology_event',
	'technology_collaboration', 'technology_process', 'technology_artifact',
	'technology_device',
	// ArchiMate — Motivation
	'stakeholder', 'driver', 'assessment', 'goal', 'outcome', 'principle',
	'requirement_archimate', 'constraint_archimate',
	// ArchiMate — Strategy
	'resource', 'capability', 'course_of_action', 'value_stream',
	// ArchiMate — Implementation & Migration
	'work_package', 'deliverable', 'implementation_event', 'plateau', 'gap',
	// C4
	'person', 'software_system', 'software_system_external', 'container',
	'c4_component', 'code_element', 'deployment_node', 'infrastructure_node',
	'container_instance',
] as const;

/** All edge type keys across all notations. */
const ALL_EDGE_TYPE_KEYS = [
	// Simple view
	'uses', 'depends_on', 'composes', 'implements', 'contains',
	// Universal
	'note_link', 'self_loop',
	// UML
	'association', 'aggregation', 'composition', 'dependency', 'realization', 'generalization', 'usage',
	// ArchiMate
	'serving', 'flow', 'triggering', 'access', 'influence',
	'archimate_realization', 'archimate_composition', 'archimate_aggregation',
	'specialization', 'assignment', 'association_archimate',
	// C4
	'c4_relationship',
] as const;

/** Unified node type registry — ALL types map to DynamicNode. */
export const unifiedNodeTypes: Record<string, Component> = Object.fromEntries(
	ALL_NODE_TYPE_KEYS.map(key => [key, DynamicNode])
);

/** Unified edge type registry — ALL types map to DynamicEdge. */
export const unifiedEdgeTypes: Record<string, Component> = Object.fromEntries(
	ALL_EDGE_TYPE_KEYS.map(key => [key, DynamicEdge])
);

/** Type equivalence map for cross-notation element compatibility. */
export const TYPE_EQUIVALENCES: Record<string, Partial<Record<string, string>>> = {
	component: { simple: 'component', uml: 'component_uml', archimate: 'application_component', c4: 'c4_component' },
	actor: { simple: 'actor', archimate: 'business_actor', c4: 'person' },
	interface: { simple: 'interface', uml: 'interface_uml', archimate: 'application_interface' },
	package: { simple: 'package', uml: 'package_uml' },
	service: { simple: 'service', archimate: 'application_service' },
};
