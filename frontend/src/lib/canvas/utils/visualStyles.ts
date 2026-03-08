/** Shared helpers to convert visual overrides to inline CSS strings. */

import type { NodeVisualOverrides, EdgeVisualOverrides } from '$lib/types/canvas';

export function nodeOverrideStyle(visual?: NodeVisualOverrides, fixedSize?: boolean): string {
	if (!visual) return '';
	const parts: string[] = [];
	if (visual.bgColor) parts.push(`background-color: ${visual.bgColor}`);
	if (visual.borderColor) parts.push(`border-color: ${visual.borderColor}`);
	if (visual.fontColor) parts.push(`color: ${visual.fontColor}`);
	if (visual.borderWidth != null) parts.push(`border-width: ${visual.borderWidth}px`);
	if (visual.fontSize != null) parts.push(`font-size: ${visual.fontSize}px`);
	if (visual.bold) parts.push('font-weight: bold');
	if (visual.italic) parts.push('font-style: italic');
	if (visual.width != null) {
		if (fixedSize) {
			parts.push(`width: ${visual.width}px`);
		} else {
			parts.push(`min-width: ${visual.width}px`);
		}
	}
	if (visual.height != null) {
		// Always use min-height to prevent content clipping — EA heights are
		// exact for the EA renderer but Iris padding/borders differ slightly.
		parts.push(`min-height: ${visual.height}px`);
	}
	return parts.join('; ');
}

export function edgeOverrideStyle(visual?: EdgeVisualOverrides): string {
	if (!visual) return '';
	const parts: string[] = [];
	if (visual.lineColor) parts.push(`stroke: ${visual.lineColor}`);
	if (visual.lineWidth != null) parts.push(`stroke-width: ${visual.lineWidth}`);
	return parts.join('; ');
}
