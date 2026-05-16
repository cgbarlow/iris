/**
 * Export utilities for model diagrams.
 *
 * Captures the content from an @xyflow/svelte canvas and converts it
 * to SVG or PNG format for download. PDF / docx / markdown exports go
 * through the server-side renderer (ADR-179, v6.2.0) via
 * `DiagramExportMenu.svelte` — the client-side `exportToPdf` path that
 * wrapped a PNG screenshot in jsPDF was removed in v6.5.0 (ADR-181)
 * because the rasterised output was worse than a real text PDF for
 * markdown-content diagrams and added zero value for visual diagrams
 * over a direct PNG.
 */

import { toPng, toSvg } from 'html-to-image';

/** Characters allowed in filenames. */
const SAFE_FILENAME_RE = /[^a-zA-Z0-9\-_. ]/g;

/**
 * Sanitise a filename by removing unsafe characters and trimming whitespace.
 * Returns 'export' if the sanitised result would be empty.
 */
export function sanitizeFilename(name: string): string {
	const cleaned = name.replace(SAFE_FILENAME_RE, '').trim();
	return cleaned.length > 0 ? cleaned : 'export';
}

/**
 * Get the viewport element from the flow container.
 * Falls back to the container itself if viewport not found.
 */
function getViewportElement(flowElement: HTMLElement): HTMLElement {
	const viewport = flowElement.querySelector('.svelte-flow__viewport') as HTMLElement | null;
	return viewport ?? flowElement;
}

/**
 * Extract the full SVG markup from a `.svelte-flow` container element.
 * The SVG element inside the container is cloned, dimensions are set to match
 * the viewport, and the serialised XML string is returned.
 *
 * Throws if no `<svg>` element is found inside the container.
 */
export function extractSvgString(flowElement: HTMLElement): string {
	const svgEl = flowElement.querySelector('svg.svelte-flow__edges');
	if (!svgEl) {
		const anySvg = flowElement.querySelector('svg');
		if (!anySvg) {
			throw new Error('No SVG element found in the flow container');
		}
		return serializeSvg(anySvg, flowElement);
	}
	return serializeSvg(svgEl as SVGSVGElement, flowElement);
}

function serializeSvg(svgEl: Element, flowElement: HTMLElement): string {
	const clone = svgEl.cloneNode(true) as SVGSVGElement;
	const { width, height } = flowElement.getBoundingClientRect();
	clone.setAttribute('width', String(width));
	clone.setAttribute('height', String(height));
	clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
	const serializer = new XMLSerializer();
	return serializer.serializeToString(clone);
}

/**
 * Trigger a file download in the browser.
 */
function downloadBlob(blob: Blob, filename: string): void {
	const url = URL.createObjectURL(blob);
	const link = document.createElement('a');
	link.href = url;
	link.download = filename;
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
	URL.revokeObjectURL(url);
}

function downloadDataUrl(dataUrl: string, filename: string): void {
	const link = document.createElement('a');
	link.href = dataUrl;
	link.download = filename;
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
}

/**
 * Export the flow canvas as an SVG file using html-to-image.
 */
export async function exportToSvg(flowElement: HTMLElement, filename: string): Promise<void> {
	const safeName = sanitizeFilename(filename);
	const viewport = getViewportElement(flowElement);
	try {
		const dataUrl = await toSvg(viewport, { cacheBust: true });
		downloadDataUrl(dataUrl, `${safeName}.svg`);
	} catch {
		// Fallback to legacy SVG extraction
		const svgString = extractSvgString(flowElement);
		const blob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
		downloadBlob(blob, `${safeName}.svg`);
	}
}

/**
 * Convert an SVG string to a PNG Blob via an offscreen canvas.
 */
export function svgToPngBlob(svgString: string, width: number, height: number): Promise<Blob> {
	return new Promise((resolve, reject) => {
		const img = new Image();
		const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
		const url = URL.createObjectURL(svgBlob);

		img.onload = () => {
			try {
				const canvas = document.createElement('canvas');
				canvas.width = width;
				canvas.height = height;
				const ctx = canvas.getContext('2d');
				if (!ctx) {
					reject(new Error('Could not get canvas 2D context'));
					return;
				}
				ctx.fillStyle = '#ffffff';
				ctx.fillRect(0, 0, width, height);
				ctx.drawImage(img, 0, 0, width, height);
				canvas.toBlob(
					(blob) => {
						if (blob) {
							resolve(blob);
						} else {
							reject(new Error('Canvas toBlob returned null'));
						}
					},
					'image/png',
				);
			} finally {
				URL.revokeObjectURL(url);
			}
		};

		img.onerror = () => {
			URL.revokeObjectURL(url);
			reject(new Error('Failed to load SVG into image for PNG conversion'));
		};

		img.src = url;
	});
}

/**
 * Export the flow canvas as a PNG file using html-to-image.
 */
export async function exportToPng(flowElement: HTMLElement, filename: string): Promise<void> {
	const safeName = sanitizeFilename(filename);
	const viewport = getViewportElement(flowElement);
	try {
		const dataUrl = await toPng(viewport, { cacheBust: true });
		downloadDataUrl(dataUrl, `${safeName}.png`);
	} catch {
		// Fallback to legacy SVG-to-PNG
		const svgString = extractSvgString(flowElement);
		const { width, height } = flowElement.getBoundingClientRect();
		const blob = await svgToPngBlob(svgString, width, height);
		downloadBlob(blob, `${safeName}.png`);
	}
}

// v6.5.0 (ADR-181): exportToPdf removed.
// Replaced by server-rendered PDF via DiagramExportMenu — the
// client-side jsPDF path wrapped a PNG screenshot of the canvas in
// an A4 sheet, which was always worse than either (a) a real text PDF
// from the server (for markdown-content diagrams) or (b) a direct PNG
// (for visual diagrams).
