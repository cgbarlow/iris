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

/** Full View UML relationship types (declared early for RelationshipTypeInfo). */
export type UmlRelationshipType =
	| 'association'
	| 'aggregation'
	| 'composition'
	| 'dependency'
	| 'realization'
	| 'generalization';

/** Full View ArchiMate relationship types (declared early for RelationshipTypeInfo). */
export type ArchimateRelationshipType =
	| 'serving'
	| 'flow'
	| 'triggering'
	| 'access'
	| 'influence'
	| 'archimate_realization'
	| 'archimate_composition'
	| 'archimate_aggregation';

/** Data stored in each canvas node. */
export interface CanvasNodeData {
	label: string;
	entityType: SimpleEntityType;
	entityId?: string;
	description?: string;
	linkedModelId?: string;
	browseMode?: boolean;
	[key: string]: unknown;
}

/** Routing algorithm for edge path rendering. */
export type EdgeRoutingType = 'default' | 'straight' | 'step' | 'smoothstep' | 'bezier';

/** Data stored in each canvas edge. */
export interface CanvasEdgeData {
	relationshipType: SimpleRelationshipType;
	relationshipId?: string;
	label?: string;
	routingType?: EdgeRoutingType;
	labelOffsetX?: number;
	labelOffsetY?: number;
	labelRotation?: number;
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
	key: SimpleRelationshipType | UmlRelationshipType | ArchimateRelationshipType;
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

/** Full View ArchiMate entity types. */
export type ArchimateEntityType =
	| 'business_actor'
	| 'business_role'
	| 'business_process'
	| 'business_service'
	| 'business_object'
	| 'application_component'
	| 'application_service'
	| 'application_interface'
	| 'technology_node'
	| 'technology_service'
	| 'technology_interface';

/** ArchiMate layer classification. */
export type ArchimateLayer = 'business' | 'application' | 'technology';

/** ArchiMate entity type display metadata. */
export interface ArchimateEntityTypeInfo {
	key: ArchimateEntityType;
	label: string;
	icon: string;
	layer: ArchimateLayer;
	description: string;
}

/** All ArchiMate entity types with display metadata. */
export const ARCHIMATE_ENTITY_TYPES: ArchimateEntityTypeInfo[] = [
	{ key: 'business_actor', label: 'Business Actor', icon: '👤', layer: 'business', description: 'Person or organisational unit' },
	{ key: 'business_role', label: 'Business Role', icon: '🎭', layer: 'business', description: 'Responsibility assigned to an actor' },
	{ key: 'business_process', label: 'Business Process', icon: '⟳', layer: 'business', description: 'Sequence of business behaviours' },
	{ key: 'business_service', label: 'Business Service', icon: '◎', layer: 'business', description: 'Externally visible business functionality' },
	{ key: 'business_object', label: 'Business Object', icon: '▤', layer: 'business', description: 'Business domain concept' },
	{ key: 'application_component', label: 'Application Component', icon: '⬡', layer: 'application', description: 'Deployable application unit' },
	{ key: 'application_service', label: 'Application Service', icon: '◎', layer: 'application', description: 'Externally visible application functionality' },
	{ key: 'application_interface', label: 'Application Interface', icon: '◯', layer: 'application', description: 'Point of access to application services' },
	{ key: 'technology_node', label: 'Technology Node', icon: '⬡', layer: 'technology', description: 'Computational or physical resource' },
	{ key: 'technology_service', label: 'Technology Service', icon: '◎', layer: 'technology', description: 'Externally visible technology functionality' },
	{ key: 'technology_interface', label: 'Technology Interface', icon: '◯', layer: 'technology', description: 'Point of access to technology services' },
];

/** All ArchiMate relationship types with display metadata. */
export const ARCHIMATE_RELATIONSHIP_TYPES: RelationshipTypeInfo[] = [
	{ key: 'serving', label: 'Serving', description: 'Source serves target' },
	{ key: 'flow', label: 'Flow', description: 'Transfer of content between elements' },
	{ key: 'triggering', label: 'Triggering', description: 'Source triggers target' },
	{ key: 'access', label: 'Access', description: 'Source accesses target data' },
	{ key: 'influence', label: 'Influence', description: 'Source influences target' },
	{ key: 'archimate_realization', label: 'Realization', description: 'Source realises target' },
	{ key: 'archimate_composition', label: 'Composition', description: 'Source composed of target' },
	{ key: 'archimate_aggregation', label: 'Aggregation', description: 'Source aggregates target' },
];
