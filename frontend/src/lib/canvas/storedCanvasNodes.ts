/**
 * Turns a diagram's stored nodes into the nodes the canvas renders
 * (issue #315, ADR-260).
 *
 * Most nodes drop their stored height: Svelte Flow then measures them
 * from their content, so a description or a wrapped title is never cut
 * off and the resize handles sit on the real box. A boundary is a
 * container with almost no content of its own, so it keeps the height it
 * was given. Without it a boundary collapses to its header.
 */
import type { CanvasNode } from '$lib/types/canvas';

const DEFAULT_NODE_WIDTH = 200;

function isBoundary(node: CanvasNode): boolean {
	return node.type === 'boundary' || node.data?.entityType === 'boundary';
}

export function storedNodesToCanvas(nodes: readonly CanvasNode[]): CanvasNode[] {
	return nodes.map((node) => {
		const { height, measured, ...rest } = node;
		const width = node.width ?? node.data?.visual?.width ?? measured?.width ?? DEFAULT_NODE_WIDTH;
		if (isBoundary(node) && height != null) return { ...rest, width, height };
		return { ...rest, width };
	});
}
