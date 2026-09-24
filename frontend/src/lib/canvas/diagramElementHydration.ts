/**
 * Canvas hydration from a diagram's elements (ADR-248, v6.50.1).
 *
 * The diagram view used to fetch `GET /api/elements/{id}` once per canvas
 * node for label/description refresh and again per node for inherited
 * tags. It now makes one `GET /api/diagrams/{id}/elements` call and feeds
 * the result through these pure helpers.
 */
import type { Element } from '$lib/types/api';
import type { CanvasNode } from '$lib/types/canvas';
import { elementToNodeData } from '$lib/canvas/elementToNodeData';

/** Node fields whose change warrants re-assigning the canvas. Presentation
 *  keys are stripped before merge (ADR-230 F1) but still compared as
 *  defence-in-depth, so a future change can't silently commit a stripped
 *  node. */
const DIFF_KEYS = [
	'label', 'description', 'diagramUsageCount',
	'attributes', 'operations', 'literals',
	'stereotype', 'qualifier',
	'visual', 'notation', 'entityType',
] as const;

/** Does any canvas node link to a model element? When not, there is
 *  nothing to fetch. */
export function hasLinkedElements(nodes: readonly CanvasNode[]): boolean {
	return nodes.some((n) => !!n.data?.entityId);
}

/**
 * Refresh every element-linked node's content from `elements` (ADR-192):
 * label, description, class compartments, stereotype, usage count.
 *
 * - Nodes without an entityId, or whose element is absent (deleted,
 *   inaccessible), are returned as-is.
 * - The node's own `visual` / `notation` / `entityType` survive: the
 *   element reports its own presentation, which is absent for EA-styled
 *   nodes whose styling lives only on the canvas (ADR-230 F1).
 * - A description that repeats the label as its first line is trimmed so
 *   BPMN-style payloads don't double-show the title.
 * - Unchanged nodes keep their identity; `updated` is false when nothing
 *   visible changed, so callers can skip a canvas re-assign.
 */
export function hydrateCanvasNodes(
	nodes: readonly CanvasNode[],
	elements: readonly Element[],
): { nodes: CanvasNode[]; updated: boolean } {
	const byId = new Map(elements.map((e) => [e.id, e]));
	let updated = false;
	const out = nodes.map((node) => {
		const entityId = node.data?.entityId;
		if (!entityId) return node;
		const element = byId.get(entityId as string);
		if (!element) return node;

		const hydrated = elementToNodeData(element);
		const rawDesc = hydrated.description;
		const desc = rawDesc.startsWith(hydrated.label)
			? rawDesc.slice(rawDesc.indexOf('\n') + 1).replace(/^\r?\n/, '')
			: rawDesc;
		const { visual: _v, notation: _n, entityType: _et, ...contentOnly } =
			hydrated as Record<string, unknown>;
		void _v; void _n; void _et;

		const prev = node.data as Record<string, unknown>;
		const next: Record<string, unknown> = { ...prev, ...contentOnly, description: desc };
		const changed = DIFF_KEYS.some((k) => JSON.stringify(next[k]) !== JSON.stringify(prev[k]));
		if (!changed) return node;
		updated = true;
		return { ...node, data: next as CanvasNode['data'] };
	});
	return { nodes: out, updated };
}

/** Tags carried by the diagram's elements that the diagram does not
 *  already have itself, sorted — shown as "inherited" tags. */
export function inheritedTagsFromElements(
	elements: readonly Element[],
	ownTags: readonly string[],
): string[] {
	const own = new Set(ownTags);
	const tags = new Set<string>();
	for (const e of elements) {
		for (const t of e.tags ?? []) {
			if (!own.has(t)) tags.add(t);
		}
	}
	return [...tags].sort();
}
