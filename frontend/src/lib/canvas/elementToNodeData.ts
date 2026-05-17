/**
 * Builds the canvas-node ``data`` payload from a backend Element
 * (ADR-192, issue #164).
 *
 * The view-detail page used to mint nodes with only label / entityType /
 * description / entityId / notation, dropping class attributes,
 * operations, literals and any visual overrides. That caused
 * inconsistencies on /views/[id] for class elements whose structured
 * payload was edited via /elements/[id] — the canvas node never
 * picked the change up.
 *
 * Single source of truth: every call site that turns an Element into
 * a node payload goes through here so the renderer (``UmlRenderer``
 * et al.) gets a complete data shape. Protocol §13 (DRY).
 */
import type { Element } from '$lib/types/api';
import type { NodeVisualOverrides, SimpleEntityType } from '$lib/types/canvas';

/** Shape consumed by the canvas renderers — compatible with CanvasNodeData. */
export interface ElementNodeData {
	label: string;
	entityType: SimpleEntityType;
	description: string;
	entityId: string;
	notation: string;
	attributes?: unknown;
	operations?: unknown;
	literals?: unknown;
	stereotype?: unknown;
	qualifier?: unknown;
	visual?: NodeVisualOverrides;
	diagramUsageCount: number;
	// CanvasNodeData has an open index signature — mirror it so this
	// type is assignable directly without a cast.
	[key: string]: unknown;
}

export function elementToNodeData(element: Element): ElementNodeData {
	const data = (element.data ?? {}) as Record<string, unknown>;
	return {
		label: element.name,
		// Backend ``element_type`` is the string form of SimpleEntityType;
		// the cast mirrors the explicit cast at the historical call sites.
		entityType: element.element_type as SimpleEntityType,
		description: element.description ?? '',
		entityId: element.id,
		notation: element.notation ?? 'simple',
		attributes: data.attributes,
		operations: data.operations,
		literals: data.literals,
		stereotype: data.stereotype,
		qualifier: data.qualifier,
		visual: data.visual as NodeVisualOverrides | undefined,
		diagramUsageCount: element.diagram_usage_count ?? 0,
	};
}
