/** Canvas data service for converting between API data and Svelte Flow nodes/edges. */

import DOMPurify from 'dompurify';
import type {
	CanvasNode,
	CanvasEdge,
	CanvasNodeData,
	CanvasEdgeData,
	ModelVersionData,
	Placement,
	SimpleEntityType,
	SimpleRelationshipType,
} from '$lib/types/canvas';

let nextNodeId = 1;

/** Generate a unique node ID. */
export function generateNodeId(): string {
	return `node-${nextNodeId++}`;
}

let nextEdgeId = 1;

/** Generate a unique edge ID. */
export function generateEdgeId(): string {
	return `edge-${nextEdgeId++}`;
}

/** Create a canvas node from entity data. */
export function createCanvasNode(
	id: string,
	label: string,
	entityType: SimpleEntityType,
	position: { x: number; y: number },
	entityId?: string,
	description?: string,
): CanvasNode {
	return {
		id,
		type: entityType,
		position,
		data: {
			label: DOMPurify.sanitize(label),
			entityType,
			entityId,
			description: description ? DOMPurify.sanitize(description) : undefined,
		},
	};
}

/** Create a canvas edge from relationship data. */
export function createCanvasEdge(
	id: string,
	sourceId: string,
	targetId: string,
	relationshipType: SimpleRelationshipType,
	relationshipId?: string,
	label?: string,
): CanvasEdge {
	return {
		id,
		source: sourceId,
		target: targetId,
		type: relationshipType,
		data: {
			relationshipType,
			relationshipId,
			label: label ? DOMPurify.sanitize(label) : undefined,
		},
	};
}

/** Convert canvas nodes to model version placements. */
export function nodesToPlacements(nodes: CanvasNode[]): Placement[] {
	return nodes.map((node) => ({
		entity_id: node.data.entityId ?? node.id,
		position: { x: node.position.x, y: node.position.y },
		size: { width: 180, height: 80 },
		visual: {},
	}));
}

/** Build a ModelVersionData structure from current canvas state. */
export function buildModelVersionData(
	nodes: CanvasNode[],
	edges: CanvasEdge[],
): ModelVersionData {
	return {
		placements: nodesToPlacements(nodes),
		displayed_relationships: edges
			.map((e) => e.data?.relationshipId)
			.filter((id): id is string => !!id),
		canvas: {
			viewport: { x: 0, y: 0, zoom: 1.0 },
			grid: { enabled: true, snap: true, size: 20 },
		},
	};
}
