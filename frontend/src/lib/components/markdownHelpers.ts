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
import { rewriteImageSrcs } from '$lib/utils/imageUrl';
import { markdownMermaidExtension } from './markdownMermaidExtension';

// ADR-149: ```mermaid fenced blocks become <pre class="mermaid-block">
// placeholders. The mermaid bundle is NOT imported here — it is
// lazy-loaded by markdownMermaidRender.ts after {@html} injects the
// placeholders into the DOM.
marked.use(markdownMermaidExtension());

export interface ExtractedLink {
	/** ADR-209 (v6.17.0): widened from {diagram|element} to the full
	 *  five-entity-type alphabet so Smart Markdown's resolved entity
	 *  references are first-class members of the link manifest. */
	kind: IrisHrefKind;
	id: string;
	label: string;
}

export interface TocHeading {
	id: string;
	level: number;
	text: string;
}

export const ALLOWED_SCHEMES = new Set(['http:', 'https:', 'mailto:', 'iris:']);

/** ADR-209 (v6.17.0): extended to all five entity types so that
 *  resolved Smart Markdown entity references click through to their
 *  detail pages. Original v6.x supported only diagram + element. */
export type IrisHrefKind = 'diagram' | 'element' | 'set' | 'package' | 'collection';

export function parseIrisHref(href: string): { kind: IrisHrefKind; id: string } | null {
	const m = /^iris:\/\/(diagram|element|set|package|collection)\/([A-Za-z0-9_\-:.]+)$/.exec(href);
	if (!m) return null;
	return { kind: m[1] as IrisHrefKind, id: m[2] };
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
	// Issue #167: defend against undefined/null. Fresh Dynamic List views
	// can arrive with no body yet; marked throws on non-string input.
	const raw = marked.parse(source ?? '', { async: false }) as string;

	// Issue #32 reopen: User Guide images use absolute paths (e.g.
	// `/guide/dashboard.png`) — those have no scheme so the original
	// scheme-only regex stripped the src. Now accepts the four allowed
	// schemes PLUS absolute (`/`) and relative (`./`, `../`) paths.
	// Path-only refs cannot carry `javascript:` or `data:` payloads
	// (no scheme to begin with). The post-walk `urlIsAllowed` is the
	// defence-in-depth layer for anchors. Tests in
	// markdownImageAllowlist.test.ts assert javascript:/data:/file:
	// remain stripped.
	const safe = DOMPurify.sanitize(raw, {
		ALLOWED_URI_REGEXP: /^(?:(?:https?|mailto|iris):|\/|\.{1,2}\/)/i,
	});

	if (typeof document === 'undefined') {
		return { html: safe, links: [] };
	}

	const tpl = document.createElement('template');
	tpl.innerHTML = safe;

	// Issue #32 reopen / protocol #7: DOMPurify allows `data:` URIs on
	// img/audio/video src by default for legitimate inline-image use,
	// even when ALLOWED_URI_REGEXP excludes them. We don't ship inline
	// data: images and they're a tracking/exfil vector — strip any img
	// src that fails the same scheme/path allowlist used for anchors.
	for (const img of tpl.content.querySelectorAll('img')) {
		const src = img.getAttribute('src') ?? '';
		if (!urlIsAllowed(src)) {
			img.removeAttribute('src');
		}
	}

	// v6.17.3 (ADR-209 follow-up): rewrite any surviving relative
	// `/api/images/<id>` src to the absolute backend URL. The frontend
	// SPA doesn't proxy /api/* in production, so a relative img src
	// loads the SPA's index.html as image bytes (broken). Smart
	// Markdown's resolver emits relative URLs server-side; this rewrite
	// is the one place to fix them all.
	tpl.innerHTML = rewriteImageSrcs(tpl.innerHTML);

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
