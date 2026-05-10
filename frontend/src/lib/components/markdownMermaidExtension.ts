/**
 * Marked extension for mermaid fenced blocks (ADR-149 / SPEC-149-A).
 *
 * Intercepts ```mermaid fences and emits a placeholder element. The
 * placeholder survives stage-1 DOMPurify with default config and is
 * replaced by the live SVG by `runMermaidIn` after `{@html}` injects
 * the sanitised HTML into the DOM.
 *
 * Placeholder shape:
 *   <pre class="mermaid-block" data-mermaid-source="<base64>">
 *     <code>...escaped source...</code>
 *   </pre>
 *
 * The base64 encoding sidesteps quote/newline pitfalls in HTML
 * attributes and survives DOMPurify with default config (no allowlist
 * widening at the markdown stage). The inner <code> preserves a
 * human-readable copy so search/select-copy works even before mermaid
 * runs (or if mermaid never runs — SSR snapshot, JS disabled, etc.).
 *
 * This module does NOT import `mermaid` — the bundle is lazy-loaded by
 * `markdownMermaidRender.ts` only when at least one placeholder is
 * actually present in the rendered DOM.
 */

import type { MarkedExtension, Tokens } from 'marked';

interface MermaidToken extends Tokens.Generic {
	type: 'mermaidBlock';
	raw: string;
	source: string;
}

const FENCE_RE = /^```mermaid[ \t]*\r?\n([\s\S]*?)\r?\n```[ \t]*(?:\r?\n|$)/;

function encodeSource(source: string): string {
	// Latin-1 → UTF-8 → base64. Symmetric with the runner's decode.
	return btoa(unescape(encodeURIComponent(source)));
}

function escapeHtml(s: string): string {
	return s
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;');
}

export function markdownMermaidExtension(): MarkedExtension {
	return {
		extensions: [
			{
				name: 'mermaidBlock',
				level: 'block',
				start(src: string) {
					const i = src.indexOf('```mermaid');
					return i === -1 ? undefined : i;
				},
				tokenizer(src: string): MermaidToken | undefined {
					const m = FENCE_RE.exec(src);
					if (!m) return undefined;
					return {
						type: 'mermaidBlock',
						raw: m[0],
						source: m[1],
					};
				},
				renderer(token: Tokens.Generic): string {
					const t = token as MermaidToken;
					const b64 = encodeSource(t.source);
					return (
						`<pre class="mermaid-block" data-mermaid-source="${b64}">` +
						`<code>${escapeHtml(t.source)}</code>` +
						`</pre>`
					);
				},
			},
		],
	};
}
