/**
 * Lazy-load mermaid runner (ADR-149 / SPEC-149-A).
 *
 * Walks `.mermaid-block` placeholders inside a given root element,
 * lazy-imports `mermaid`, calls `mermaid.render()` per block,
 * sanitises the output SVG via stage-2 DOMPurify, and replaces the
 * placeholder. Errors are caught per-block and rendered as a
 * `.mermaid-error` element so the rest of the document survives one
 * bad diagram.
 *
 * Lazy-load contract: zero placeholders → zero mermaid imports. The
 * dynamic import promise is cached at module scope after the first
 * call so subsequent renders reuse the resolved bundle.
 */

import DOMPurify from 'dompurify';

export type MermaidTheme = 'default' | 'dark';

interface MermaidLib {
	initialize: (config: Record<string, unknown>) => void;
	render: (id: string, source: string) => Promise<{ svg: string; bindFunctions?: unknown }>;
}

let mermaidPromise: Promise<MermaidLib> | null = null;
let renderCounter = 0;

function loadMermaid(): Promise<MermaidLib> {
	if (!mermaidPromise) {
		mermaidPromise = import('mermaid').then((mod) => {
			const lib = (mod.default ?? mod) as MermaidLib;
			return lib;
		});
	}
	return mermaidPromise;
}

// foreignObject is added explicitly because mermaid uses it for HTML
// labels in flowcharts. Mermaid runs in securityLevel: 'strict' so the
// HTML inside foreignObject is mermaid-controlled, but we still strip
// <script>/event-handlers as defence-in-depth.
const SVG_PURIFY_CONFIG = {
	USE_PROFILES: { svg: true, svgFilters: true },
	ADD_TAGS: ['foreignObject'],
} as const;

export function sanitiseMermaidSvg(svg: string): string {
	return DOMPurify.sanitize(svg, SVG_PURIFY_CONFIG) as string;
}

function decodeSource(b64: string): string {
	return decodeURIComponent(escape(atob(b64)));
}

function makeError(message: string): HTMLDivElement {
	const div = document.createElement('div');
	div.className = 'mermaid-error';
	div.setAttribute('role', 'alert');
	const strong = document.createElement('strong');
	strong.textContent = 'Mermaid render error: ';
	const code = document.createElement('code');
	code.textContent = message;
	div.appendChild(strong);
	div.appendChild(code);
	return div;
}

/**
 * Walk `.mermaid-block` placeholders inside `rootEl` and render them.
 * Idempotent: the placeholder is replaced with its rendered SVG (or
 * an error div) on the first run, so subsequent calls find no
 * placeholders unless `rootEl.innerHTML` was reset (e.g. new markdown
 * source).
 */
export async function runMermaidIn(rootEl: HTMLElement, theme: MermaidTheme): Promise<void> {
	const placeholders = rootEl.querySelectorAll<HTMLElement>('pre.mermaid-block[data-mermaid-source]');
	if (placeholders.length === 0) return;

	const mermaid = await loadMermaid();
	mermaid.initialize({
		startOnLoad: false,
		securityLevel: 'strict',
		theme,
		suppressErrorRendering: true,
	});

	for (const placeholder of placeholders) {
		const b64 = placeholder.getAttribute('data-mermaid-source') ?? '';
		const source = decodeSource(b64);
		const id = `iris-mermaid-${++renderCounter}`;

		try {
			const { svg } = await mermaid.render(id, source);
			const safe = sanitiseMermaidSvg(svg);
			placeholder.innerHTML = safe;
		} catch (err) {
			const message = err instanceof Error ? err.message : String(err);
			placeholder.replaceWith(makeError(message));
		}
	}
}
