/** Canvas type definitions for Svelte Flow integration. */

import type { Node, Edge } from '@xyflow/svelte';

/** Simple View entity types. */
export type SimpleEntityType =
	| 'component'
	| 'service'
	| 'interface'
	| 'package'
	| 'actor'
	| 'database'
	| 'queue';

/** Simple View relationship types. */
export type SimpleRelationshipType = 'uses' | 'depends_on' | 'composes' | 'implements' | 'contains';

/** Data stored in each canvas node. */
export interface CanvasNodeData {
	label: string;
	entityType: SimpleEntityType;
	entityId?: string;
	description?: string;
	[key: string]: unknown;
}

/** Data stored in each canvas edge. */
export interface CanvasEdgeData {
	relationshipType: SimpleRelationshipType;
	relationshipId?: string;
	label?: string;
	[key: string]: unknown;
}

/** Typed canvas node. */
export type CanvasNode = Node<CanvasNodeData>;

/** Typed canvas edge. */
export type CanvasEdge = Edge<CanvasEdgeData>;

/** Placement stored in model version JSON. */
export interface Placement {
	entity_id: string;
	position: { x: number; y: number };
	size: { width: number; height: number };
	visual: Record<string, unknown>;
}

/** Canvas viewport and grid settings from model version JSON. */
export interface CanvasSettings {
	viewport: { x: number; y: number; zoom: number };
	grid: { enabled: boolean; snap: boolean; size: number };
}

/** Full model version data structure. */
export interface ModelVersionData {
	placements: Placement[];
	displayed_relationships: string[];
	canvas: CanvasSettings;
}

/** Entity type display metadata. */
export interface EntityTypeInfo {
	key: SimpleEntityType;
	label: string;
	icon: string;
	description: string;
}

/** All Simple View entity types with display metadata. */
export const SIMPLE_ENTITY_TYPES: EntityTypeInfo[] = [
	{ key: 'component', label: 'Component', icon: '⬡', description: 'A modular unit of software' },
	{ key: 'service', label: 'Service', icon: '◎', description: 'A deployed or logical service' },
	{
		key: 'interface',
		label: 'Interface',
		icon: '◯',
		description: 'A contract or API surface',
	},
	{ key: 'package', label: 'Package', icon: '▤', description: 'A grouping container' },
	{ key: 'actor', label: 'Actor', icon: '👤', description: 'A person or external system' },
	{ key: 'database', label: 'Database', icon: '▦', description: 'A persistent data store' },
	{ key: 'queue', label: 'Queue', icon: '≋', description: 'An asynchronous message channel' },
];

/** Relationship type display metadata. */
export interface RelationshipTypeInfo {
	key: SimpleRelationshipType | UmlRelationshipType;
	label: string;
	description: string;
}

/** All Simple View relationship types with display metadata. */
export const SIMPLE_RELATIONSHIP_TYPES: RelationshipTypeInfo[] = [
	{ key: 'uses', label: 'Uses', description: 'Source uses/depends on target' },
	{ key: 'depends_on', label: 'Depends On', description: 'Source depends on target' },
	{ key: 'composes', label: 'Composes', description: 'Source is composed of target' },
	{ key: 'implements', label: 'Implements', description: 'Source implements target interface' },
	{ key: 'contains', label: 'Contains', description: 'Source contains target (nesting)' },
];

/** Full View UML entity types. */
export type UmlEntityType = 'class' | 'object' | 'use_case' | 'state' | 'activity' | 'node';

/** Full View UML relationship types. */
export type UmlRelationshipType =
	| 'association'
	| 'aggregation'
	| 'composition'
	| 'dependency'
	| 'realization'
	| 'generalization';

/** UML class compartment data. */
export interface ClassCompartments {
	attributes?: string[];
	operations?: string[];
}

/** UML entity type display metadata. */
export interface UmlEntityTypeInfo {
	key: UmlEntityType;
	label: string;
	icon: string;
	description: string;
}

/** All UML entity types with display metadata. */
export const UML_ENTITY_TYPES: UmlEntityTypeInfo[] = [
	{ key: 'class', label: 'Class', icon: '▭', description: 'UML class with attributes and operations' },
	{ key: 'object', label: 'Object', icon: '▯', description: 'Instance of a class' },
	{ key: 'use_case', label: 'Use Case', icon: '◎', description: 'User goal or system function' },
	{ key: 'state', label: 'State', icon: '◉', description: 'Condition during object life' },
	{ key: 'activity', label: 'Activity', icon: '▷', description: 'Action or workflow step' },
	{ key: 'node', label: 'Node', icon: '⬡', description: 'Computational resource' },
];

/** All UML relationship types with display metadata. */
export const UML_RELATIONSHIP_TYPES: RelationshipTypeInfo[] = [
	{ key: 'association', label: 'Association', description: 'Structural link between classes' },
	{ key: 'aggregation', label: 'Aggregation', description: 'Whole-part (weak ownership)' },
	{ key: 'composition', label: 'Composition', description: 'Whole-part (strong ownership)' },
	{ key: 'dependency', label: 'Dependency', description: 'Source depends on target' },
	{ key: 'realization', label: 'Realization', description: 'Source implements target spec' },
	{ key: 'generalization', label: 'Generalization', description: 'Source inherits from target' },
];
