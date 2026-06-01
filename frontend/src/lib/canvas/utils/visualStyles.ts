/** Shared helpers to convert visual overrides to inline CSS strings. */

import type { NodeVisualOverrides, EdgeVisualOverrides } from '$lib/types/canvas';

export function nodeOverrideStyle(visual?: NodeVisualOverrides, fixedSize?: boolean): string {
	if (!visual) return 'width: 100%; height: 100%';
	const parts: string[] = ['width: 100%', 'height: 100%'];
	if (visual.bgColor) parts.push(`background-color: ${visual.bgColor}`);
	if (visual.borderColor) parts.push(`border-color: ${visual.borderColor}`);
	if (visual.fontColor) parts.push(`color: ${visual.fontColor}`);
	if (visual.borderWidth != null) parts.push(`border-width: ${visual.borderWidth}px`);
	if (visual.borderStyle) parts.push(`border-style: ${visual.borderStyle}`);
	// Corner radius / pill (ADR-230 F2). 'pill' wins over an explicit radius.
	if (visual.cornerStyle === 'pill') parts.push('border-radius: 9999px');
	else if (visual.cornerStyle === 'sharp') parts.push('border-radius: 0');
	else if (visual.borderRadius != null) parts.push(`border-radius: ${visual.borderRadius}px`);
	if (visual.fontSize != null && visual.fontSize > 0) parts.push(`font-size: ${visual.fontSize}px`);
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

/** Inline style for title/label elements based on visual overrides. */
export function titleFontStyle(visual?: NodeVisualOverrides): string {
	if (!visual) return '';
	const parts: string[] = [];
	if (visual.fontColor) parts.push(`color: ${visual.fontColor}`);
	if (visual.fontSize != null && visual.fontSize > 0) parts.push(`font-size: ${visual.fontSize}px`);
	if (visual.bold) parts.push('font-weight: bold');
	if (visual.italic) parts.push('font-style: italic');
	return parts.join('; ');
}

/** Inline style for description elements based on visual overrides. */
export function descFontStyle(visual?: NodeVisualOverrides): string {
	if (!visual) return '';
	const parts: string[] = [];
	if (visual.descFontColor) parts.push(`color: ${visual.descFontColor}`);
	if (visual.descFontSize != null && visual.descFontSize > 0) parts.push(`font-size: ${visual.descFontSize}px`);
	if (visual.descBold) parts.push('font-weight: bold');
	else if (visual.descBold === false) parts.push('font-weight: normal');
	if (visual.descItalic) parts.push('font-style: italic');
	else if (visual.descItalic === false) parts.push('font-style: normal');
	return parts.join('; ');
}

export function edgeOverrideStyle(visual?: EdgeVisualOverrides): string {
	if (!visual) return '';
	const parts: string[] = [];
	if (visual.lineColor) parts.push(`stroke: ${visual.lineColor}`);
	if (visual.lineWidth != null) parts.push(`stroke-width: ${visual.lineWidth}`);
	return parts.join('; ');
}
