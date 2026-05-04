/**
 * Pure helpers for MarkdownView (ADR-137). Extracted so they can be unit
 * tested without mounting the Svelte component.
 *
 * Pipeline used by MarkdownView:
 *   markdown source → marked.parse → DOMPurify (with iris:// + http(s) +
 *   mailto whitelist) → walk anchors to tag iris:// targets and enforce
 *   the URL-scheme allowlist a second time as defence-in-depth.
 *
 * Headings are extracted directly from the source so the TOC reflects
 * authored order even when fenced-code blocks contain heading-like
 * lines.
 */

import { marked } from 'marked';
import DOMPurify from 'dompurify';

export interface ExtractedLink {
	kind: 'diagram' | 'element';
	id: string;
	label: string;
}

export interface TocHeading {
	id: string;
	level: number;
	text: string;
}

export const ALLOWED_SCHEMES = new Set(['http:', 'https:', 'mailto:', 'iris:']);

export function parseIrisHref(href: string): { kind: 'diagram' | 'element'; id: string } | null {
	const m = /^iris:\/\/(diagram|element)\/([A-Za-z0-9_\-:.]+)$/.exec(href);
	if (!m) return null;
	return { kind: m[1] as 'diagram' | 'element', id: m[2] };
}

export function urlIsAllowed(href: string): boolean {
	try {
		const u = new URL(href, 'https://placeholder.example/');
		return ALLOWED_SCHEMES.has(u.protocol);
	} catch {
		return true;
	}
}

export function extractHeadings(source: string): TocHeading[] {
	const out: TocHeading[] = [];
	const lines = source.split(/\r?\n/);
	let inFence = false;
	const slugCounts = new Map<string, number>();
	const slug = (s: string) => {
		const base = s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '') || 'h';
		const n = (slugCounts.get(base) ?? 0) + 1;
		slugCounts.set(base, n);
		return n === 1 ? base : `${base}-${n}`;
	};
	for (const line of lines) {
		if (/^```/.test(line.trim())) { inFence = !inFence; continue; }
		if (inFence) continue;
		const m = /^(#{1,6})\s+(.+?)\s*#*\s*$/.exec(line);
		if (!m) continue;
		out.push({ id: slug(m[2].trim()), level: m[1].length, text: m[2].trim() });
	}
	return out;
}

export interface RenderedMarkdown {
	html: string;
	links: ExtractedLink[];
}

/**
 * Run the full sanitise + iris:// rewrite pipeline. Returns the safe
 * HTML string and the iris:// links discovered in it.
 *
 * `textDiagramIds` is the optional set of diagram IDs that are
 * Text-class — their refs get the `md-iris-link--text` class so the
 * caller's CSS can apply muted colour (issue #26).
 */
export function renderMarkdown(source: string, textDiagramIds?: Set<string>): RenderedMarkdown {
	const raw = marked.parse(source, { async: false }) as string;

	const safe = DOMPurify.sanitize(raw, {
		ALLOWED_URI_REGEXP: /^(?:https?|mailto|iris):/i,
	});

	if (typeof document === 'undefined') {
		return { html: safe, links: [] };
	}

	const tpl = document.createElement('template');
	tpl.innerHTML = safe;

	const links: ExtractedLink[] = [];
	for (const a of tpl.content.querySelectorAll('a')) {
		const href = a.getAttribute('href') ?? '';
		if (!urlIsAllowed(href)) {
			a.removeAttribute('href');
			continue;
		}
		const irisLink = parseIrisHref(href);
		if (!irisLink) continue;
		const label = a.textContent ?? '';
		links.push({ ...irisLink, label });
		a.classList.add('md-iris-link');
		a.classList.add(`md-iris-link--${irisLink.kind}`);
		a.setAttribute('data-iris-kind', irisLink.kind);
		a.setAttribute('data-iris-id', irisLink.id);
		if (irisLink.kind === 'diagram' && textDiagramIds?.has(irisLink.id)) {
			a.classList.add('md-iris-link--text');
		}
	}

	return { html: tpl.innerHTML, links };
}
