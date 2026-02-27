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
	key: SimpleRelationshipType;
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
