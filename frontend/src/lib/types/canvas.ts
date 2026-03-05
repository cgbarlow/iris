/** Canvas type definitions for Svelte Flow integration. */

import type { Node, Edge } from '@xyflow/svelte';

/** Diagram notation type — determines how elements render on canvas. */
export type NotationType = 'simple' | 'uml' | 'archimate' | 'c4';

/** Simple View entity types (5 domain + 2 universal = 7 total). */
export type SimpleEntityType =
	| 'component'
	| 'service'
	| 'interface'
	| 'actor'
	| 'database'
	| 'note'
	| 'boundary';

/** Simple View relationship types (4 types — non-technical mode). */
export type SimpleRelationshipType = 'uses' | 'depends_on' | 'contains' | 'note_link';

/** Full View UML relationship types (declared early for RelationshipTypeInfo). */
export type UmlRelationshipType =
	| 'association'
	| 'aggregation'
	| 'composition'
	| 'dependency'
	| 'realization'
	| 'generalization'
	| 'usage';

/** Full View ArchiMate relationship types (declared early for RelationshipTypeInfo). */
export type ArchimateRelationshipType =
	| 'serving'
	| 'flow'
	| 'triggering'
	| 'access'
	| 'influence'
	| 'archimate_realization'
	| 'archimate_composition'
	| 'archimate_aggregation'
	| 'specialization'
	| 'assignment'
	| 'association_archimate';

/** Data stored in each canvas node. */
export interface CanvasNodeData {
	label: string;
	entityType: SimpleEntityType;
	entityId?: string;
	description?: string;
	linkedModelId?: string;
	browseMode?: boolean;
	notation?: string;
	[key: string]: unknown;
}

/** Routing algorithm for edge path rendering. */
export type EdgeRoutingType = 'default' | 'straight' | 'step' | 'smoothstep' | 'bezier';

/** Data stored in each canvas edge. */
export interface CanvasEdgeData {
	relationshipType: SimpleRelationshipType;
	relationshipId?: string;
	modelRelationshipId?: string;
	label?: string;
	routingType?: EdgeRoutingType;
	labelOffsetX?: number;
	labelOffsetY?: number;
	labelRotation?: number;
	/** SparxEA connector metadata (ADR-070). */
	sourceCardinality?: string;
	targetCardinality?: string;
	sourceRole?: string;
	targetRole?: string;
	stereotype?: string;
	direction?: string;
	technology?: string;
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

/** All Simple View entity types with display metadata (5 domain + 2 universal). */
export const SIMPLE_ENTITY_TYPES: EntityTypeInfo[] = [
	{ key: 'component', label: 'Component', icon: '⬡', description: 'A modular unit or generic box' },
	{ key: 'service', label: 'Service', icon: '◎', description: 'A deployed or logical service' },
	{ key: 'interface', label: 'Interface', icon: '◯', description: 'An API or contract' },
	{ key: 'actor', label: 'Actor', icon: '👤', description: 'A person or external system' },
	{ key: 'database', label: 'Database', icon: '▦', description: 'A data store' },
	{ key: 'note', label: 'Note', icon: '📝', description: 'An annotation or documentation note' },
	{ key: 'boundary', label: 'Boundary', icon: '▧', description: 'A visual grouping boundary' },
];

/** Relationship type display metadata. */
export interface RelationshipTypeInfo {
	key: SimpleRelationshipType | UmlRelationshipType | ArchimateRelationshipType;
	label: string;
	description: string;
}

/** All Simple View relationship types with display metadata (4 types). */
export const SIMPLE_RELATIONSHIP_TYPES: RelationshipTypeInfo[] = [
	{ key: 'uses', label: 'Uses', description: 'A uses B' },
	{ key: 'depends_on', label: 'Depends On', description: 'A depends on B' },
	{ key: 'contains', label: 'Contains', description: 'A contains B (for boundary grouping)' },
	{ key: 'note_link', label: 'Note Link', description: 'Attaches a note to an element' },
];

/** Full View UML entity types. */
export type UmlEntityType = 'class' | 'object' | 'use_case' | 'state' | 'activity' | 'node' | 'interface_uml' | 'enumeration' | 'abstract_class' | 'component_uml' | 'package_uml';

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
	{ key: 'interface_uml', label: 'Interface', icon: '◯', description: 'Contract specifying operations' },
	{ key: 'enumeration', label: 'Enumeration', icon: '▤', description: 'Set of named literal values' },
	{ key: 'abstract_class', label: 'Abstract Class', icon: '▭', description: 'Class that cannot be instantiated' },
	{ key: 'component_uml', label: 'Component', icon: '⊞', description: 'Modular deployable unit' },
	{ key: 'package_uml', label: 'Package', icon: '▤', description: 'Namespace grouping container' },
];

/** All UML relationship types with display metadata. */
export const UML_RELATIONSHIP_TYPES: RelationshipTypeInfo[] = [
	{ key: 'association', label: 'Association', description: 'Structural link between classes' },
	{ key: 'aggregation', label: 'Aggregation', description: 'Whole-part (weak ownership)' },
	{ key: 'composition', label: 'Composition', description: 'Whole-part (strong ownership)' },
	{ key: 'dependency', label: 'Dependency', description: 'Source depends on target' },
	{ key: 'realization', label: 'Realization', description: 'Source implements target spec' },
	{ key: 'generalization', label: 'Generalization', description: 'Source inherits from target' },
	{ key: 'usage', label: 'Usage', description: 'Source uses target' },
];

/** Full View ArchiMate entity types. */
export type ArchimateEntityType =
	| 'business_actor'
	| 'business_role'
	| 'business_process'
	| 'business_service'
	| 'business_object'
	| 'business_function'
	| 'business_interaction'
	| 'business_event'
	| 'business_collaboration'
	| 'business_interface'
	| 'application_component'
	| 'application_service'
	| 'application_interface'
	| 'application_function'
	| 'application_interaction'
	| 'application_event'
	| 'application_collaboration'
	| 'application_process'
	| 'technology_node'
	| 'technology_service'
	| 'technology_interface'
	| 'technology_function'
	| 'technology_interaction'
	| 'technology_event'
	| 'technology_collaboration'
	| 'technology_process'
	| 'technology_artifact'
	| 'technology_device'
	| 'stakeholder'
	| 'driver'
	| 'assessment'
	| 'goal'
	| 'outcome'
	| 'principle'
	| 'requirement_archimate'
	| 'constraint_archimate'
	| 'resource'
	| 'capability'
	| 'course_of_action'
	| 'value_stream'
	| 'work_package'
	| 'deliverable'
	| 'implementation_event'
	| 'plateau'
	| 'gap';

/** ArchiMate layer classification. */
export type ArchimateLayer = 'business' | 'application' | 'technology' | 'motivation' | 'strategy' | 'implementation_migration';

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
	/* ── Business Layer ── */
	{ key: 'business_actor', label: 'Business Actor', icon: '👤', layer: 'business', description: 'Person or organisational unit' },
	{ key: 'business_role', label: 'Business Role', icon: '🎭', layer: 'business', description: 'Responsibility assigned to an actor' },
	{ key: 'business_process', label: 'Business Process', icon: '⟳', layer: 'business', description: 'Sequence of business behaviours' },
	{ key: 'business_service', label: 'Business Service', icon: '◎', layer: 'business', description: 'Externally visible business functionality' },
	{ key: 'business_object', label: 'Business Object', icon: '▤', layer: 'business', description: 'Business domain concept' },
	{ key: 'business_function', label: 'Business Function', icon: '⨍', layer: 'business', description: 'Collection of business behaviour' },
	{ key: 'business_interaction', label: 'Business Interaction', icon: '⇄', layer: 'business', description: 'Behaviour element performed by collaborating roles' },
	{ key: 'business_event', label: 'Business Event', icon: '⚡', layer: 'business', description: 'Business state change' },
	{ key: 'business_collaboration', label: 'Business Collaboration', icon: '⊕', layer: 'business', description: 'Aggregate of two or more business roles' },
	{ key: 'business_interface', label: 'Business Interface', icon: '◯', layer: 'business', description: 'Point of access to business services' },
	/* ── Application Layer ── */
	{ key: 'application_component', label: 'Application Component', icon: '⬡', layer: 'application', description: 'Deployable application unit' },
	{ key: 'application_service', label: 'Application Service', icon: '◎', layer: 'application', description: 'Externally visible application functionality' },
	{ key: 'application_interface', label: 'Application Interface', icon: '◯', layer: 'application', description: 'Point of access to application services' },
	{ key: 'application_function', label: 'Application Function', icon: '⨍', layer: 'application', description: 'Automated behaviour element' },
	{ key: 'application_interaction', label: 'Application Interaction', icon: '⇄', layer: 'application', description: 'Behaviour element performed by collaborating components' },
	{ key: 'application_event', label: 'Application Event', icon: '⚡', layer: 'application', description: 'Application state change' },
	{ key: 'application_collaboration', label: 'Application Collaboration', icon: '⊕', layer: 'application', description: 'Aggregate of two or more application components' },
	{ key: 'application_process', label: 'Application Process', icon: '⟳', layer: 'application', description: 'Sequence of application behaviours' },
	/* ── Technology Layer ── */
	{ key: 'technology_node', label: 'Technology Node', icon: '⬡', layer: 'technology', description: 'Computational or physical resource' },
	{ key: 'technology_service', label: 'Technology Service', icon: '◎', layer: 'technology', description: 'Externally visible technology functionality' },
	{ key: 'technology_interface', label: 'Technology Interface', icon: '◯', layer: 'technology', description: 'Point of access to technology services' },
	{ key: 'technology_function', label: 'Technology Function', icon: '⨍', layer: 'technology', description: 'Collection of technology behaviour' },
	{ key: 'technology_interaction', label: 'Technology Interaction', icon: '⇄', layer: 'technology', description: 'Behaviour element performed by collaborating nodes' },
	{ key: 'technology_event', label: 'Technology Event', icon: '⚡', layer: 'technology', description: 'Technology state change' },
	{ key: 'technology_collaboration', label: 'Technology Collaboration', icon: '⊕', layer: 'technology', description: 'Aggregate of two or more technology nodes' },
	{ key: 'technology_process', label: 'Technology Process', icon: '⟳', layer: 'technology', description: 'Sequence of technology behaviours' },
	{ key: 'technology_artifact', label: 'Technology Artifact', icon: '▤', layer: 'technology', description: 'Piece of data used or produced' },
	{ key: 'technology_device', label: 'Technology Device', icon: '▣', layer: 'technology', description: 'Physical computational resource' },
	/* ── Motivation Layer ── */
	{ key: 'stakeholder', label: 'Stakeholder', icon: '♦', layer: 'motivation', description: 'Role of an individual, team, or organisation with interests' },
	{ key: 'driver', label: 'Driver', icon: '⚡', layer: 'motivation', description: 'External or internal condition that motivates change' },
	{ key: 'assessment', label: 'Assessment', icon: '◈', layer: 'motivation', description: 'Result of analysis of a driver' },
	{ key: 'goal', label: 'Goal', icon: '★', layer: 'motivation', description: 'High-level statement of intent or direction' },
	{ key: 'outcome', label: 'Outcome', icon: '✦', layer: 'motivation', description: 'End result that is achievable and measurable' },
	{ key: 'principle', label: 'Principle', icon: '⊕', layer: 'motivation', description: 'Qualitative statement of intent for the architecture' },
	{ key: 'requirement_archimate', label: 'Requirement', icon: '⊡', layer: 'motivation', description: 'Statement of need that must be met' },
	{ key: 'constraint_archimate', label: 'Constraint', icon: '⊠', layer: 'motivation', description: 'Factor limiting the realisation of goals' },
	/* ── Strategy Layer ── */
	{ key: 'resource', label: 'Resource', icon: '◆', layer: 'strategy', description: 'Asset owned or controlled by an individual or organisation' },
	{ key: 'capability', label: 'Capability', icon: '⬢', layer: 'strategy', description: 'Ability that an organisation possesses' },
	{ key: 'course_of_action', label: 'Course of Action', icon: '➤', layer: 'strategy', description: 'Approach or plan for achieving a goal' },
	{ key: 'value_stream', label: 'Value Stream', icon: '≡', layer: 'strategy', description: 'Sequence of activities creating an overall result' },
	/* ── Implementation & Migration Layer ── */
	{ key: 'work_package', label: 'Work Package', icon: '▣', layer: 'implementation_migration', description: 'Series of actions to achieve a result' },
	{ key: 'deliverable', label: 'Deliverable', icon: '◧', layer: 'implementation_migration', description: 'Precisely defined output of a work package' },
	{ key: 'implementation_event', label: 'Implementation Event', icon: '⚑', layer: 'implementation_migration', description: 'State change during implementation' },
	{ key: 'plateau', label: 'Plateau', icon: '▬', layer: 'implementation_migration', description: 'Relatively stable state of the architecture' },
	{ key: 'gap', label: 'Gap', icon: '△', layer: 'implementation_migration', description: 'Difference between two plateaus' },
];

/** C4 entity types. */
export type C4EntityType =
	| 'person'
	| 'software_system'
	| 'software_system_external'
	| 'container'
	| 'c4_component'
	| 'code_element'
	| 'deployment_node'
	| 'infrastructure_node'
	| 'container_instance';

/** C4 level classification. */
export type C4Level = 'system_context' | 'container' | 'component' | 'code' | 'deployment';

/** C4 entity type display metadata. */
export interface C4EntityTypeInfo {
	key: C4EntityType;
	label: string;
	icon: string;
	level: C4Level;
	description: string;
}

/** All C4 entity types with display metadata. */
export const C4_ENTITY_TYPES: C4EntityTypeInfo[] = [
	{ key: 'person', label: 'Person', icon: '👤', level: 'system_context', description: 'A user or actor interacting with the system' },
	{ key: 'software_system', label: 'Software System', icon: '▣', level: 'system_context', description: 'An overall software system (internal)' },
	{ key: 'software_system_external', label: 'External System', icon: '▢', level: 'system_context', description: 'An external system outside your control' },
	{ key: 'container', label: 'Container', icon: '▤', level: 'container', description: 'An application, data store, or service' },
	{ key: 'c4_component', label: 'Component', icon: '⬡', level: 'component', description: 'A module or service within a container' },
	{ key: 'code_element', label: 'Code Element', icon: '▭', level: 'code', description: 'A class, interface, or function' },
	{ key: 'deployment_node', label: 'Deployment Node', icon: '⬢', level: 'deployment', description: 'Server, VM, container platform, or cloud region' },
	{ key: 'infrastructure_node', label: 'Infrastructure Node', icon: '◆', level: 'deployment', description: 'Load balancer, firewall, or DNS' },
	{ key: 'container_instance', label: 'Container Instance', icon: '▥', level: 'deployment', description: 'Running instance of a container' },
];

/** Simple diagram-type → allowed element type keys (ADR-082). null = no filtering.
 *  Note and boundary are universal annotation types, always available on any diagram. */
export const SIMPLE_DIAGRAM_TYPE_FILTER: Record<string, string[] | null> = {
	component: ['component', 'service', 'interface', 'actor', 'database'],
	sequence: ['component', 'service', 'actor'],
	deployment: ['component', 'service', 'database'],
	process: ['component', 'service', 'actor'],
	roadmap: ['component', 'service'],
	use_case: ['component', 'service', 'actor'],
	state_machine: ['component', 'service'],
	system_context: ['component', 'service', 'actor', 'database'],
	container: ['component', 'service', 'database'],
	free_form: null,
};

/** UML diagram-type → allowed element type keys (ADR-082). null = no filtering. */
export const UML_DIAGRAM_TYPE_FILTER: Record<string, string[] | null> = {
	component: ['component_uml', 'interface_uml', 'package_uml', 'node'],
	sequence: ['class', 'object', 'component_uml', 'interface_uml'],
	class: ['class', 'object', 'interface_uml', 'enumeration', 'abstract_class', 'package_uml'],
	deployment: ['node', 'component_uml'],
	process: ['activity', 'state'],
	use_case: ['use_case', 'component_uml', 'package_uml'],
	state_machine: ['state'],
	free_form: null,
};

/** ArchiMate diagram-type → allowed layers (ADR-082). null = no filtering. */
export const ARCHIMATE_DIAGRAM_TYPE_LAYERS: Record<string, string[] | null> = {
	component: ['application', 'technology', 'business'],
	deployment: ['technology'],
	process: ['business', 'application', 'technology'],
	roadmap: ['implementation_migration', 'strategy'],
	motivation: ['motivation'],
	strategy: ['strategy'],
	free_form: null,
};

/** C4 diagram-type → allowed levels (ADR-082). null = no filtering. */
export const C4_DIAGRAM_TYPE_LEVELS: Record<string, string[] | null> = {
	system_context: ['system_context'],
	container: ['system_context', 'container'],
	component: ['container', 'component'],
	deployment: ['deployment'],
	sequence: ['system_context', 'container', 'component', 'code'],
	free_form: null,
};

/** C4 relationship type. */
export type C4RelationshipType = 'c4_relationship';

/** All C4 relationship types with display metadata. */
export const C4_RELATIONSHIP_TYPES: RelationshipTypeInfo[] = [
	{ key: 'c4_relationship' as C4RelationshipType, label: 'Relationship', description: 'Labeled relationship with optional technology annotation' },
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
	{ key: 'specialization', label: 'Specialization', description: 'Source specialises target' },
	{ key: 'assignment', label: 'Assignment', description: 'Source assigned to target' },
	{ key: 'association_archimate', label: 'Association', description: 'Unspecified relationship' },
];
