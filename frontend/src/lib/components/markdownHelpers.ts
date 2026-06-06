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

/** A fresh slugger with its own dedup counter. Shared by extractHeadings and
 *  renderMarkdown — walked in the same (document) order — so the TOC entry ids
 *  match the ids assigned to the rendered heading elements, and TOC jumps land. */
export function makeSlugger(): (s: string) => string {
	const counts = new Map<string, number>();
	return (s: string) => {
		const base = s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '') || 'h';
		const n = (counts.get(base) ?? 0) + 1;
		counts.set(base, n);
		return n === 1 ? base : `${base}-${n}`;
	};
}

/** Flatten inline markdown to plain text for TOC display: links/images keep
 *  their label/alt; emphasis, inline code, and strikethrough markers are
 *  dropped. So a heading authored as `Security (CSE) · [13](iris://diagram/…)`
 *  reads `Security (CSE) · 13` in the TOC instead of leaking the raw link
 *  syntax (ADR-137 follow-up). */
export function stripInlineMarkdown(s: string): string {
	return s
		.replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1') // images → alt text
		.replace(/\[([^\]]+)\]\([^)]*\)/g, '$1') // links → label
		.replace(/`([^`]+)`/g, '$1') // inline code
		.replace(/(\*\*|__)(.*?)\1/g, '$2') // bold
		.replace(/(\*|_)(.*?)\1/g, '$2') // italic
		.replace(/~~(.*?)~~/g, '$2') // strikethrough
		.trim();
}

export function extractHeadings(source: string): TocHeading[] {
	const out: TocHeading[] = [];
	const lines = source.split(/\r?\n/);
	let inFence = false;
	const slug = makeSlugger();
	for (const line of lines) {
		if (/^```/.test(line.trim())) { inFence = !inFence; continue; }
		if (inFence) continue;
		const m = /^(#{1,6})\s+(.+?)\s*#*\s*$/.exec(line);
		if (!m) continue;
		const text = stripInlineMarkdown(m[2].trim());
		out.push({ id: slug(text), level: m[1].length, text });
	}
	return out;
}

export interface RenderedMarkdown {
	html: string;
	links: ExtractedLink[];
}

// ─── Issue #255 / ADR-239: checklist mode ──────────────────────────────
//
// State lives as native GFM task markers (`- [ ]` / `- [x]`) in the
// markdown SOURCE — portable, exports cleanly, and survives Smart
// Markdown token resolution (which is a splice that preserves list-item
// order/count). `toggleChecklistItem` rewrites the source; the rendered
// view is decorated client-side by `decorateChecklist`.

/** A markdown list-item line: indent, bullet, then the remainder text. */
const LIST_ITEM_RE = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/;
/** A leading GFM task marker on a list item's remainder. */
const TASK_MARKER_RE = /^\[([ xX])\]\s?/;

/** Walk source lines, invoking `visit` for each list-item line that is NOT
 *  inside a fenced code block. Document order; mirrors extractHeadings'
 *  fence handling so a `- [ ]`-looking line inside ``` ``` ``` is ignored. */
function eachListItem(
	source: string,
	visit: (lineIndex: number, match: RegExpExecArray) => void,
): void {
	const lines = (source ?? '').split(/\r?\n/);
	let inFence = false;
	for (let i = 0; i < lines.length; i++) {
		if (/^(```|~~~)/.test(lines[i].trim())) { inFence = !inFence; continue; }
		if (inFence) continue;
		const m = LIST_ITEM_RE.exec(lines[i]);
		if (m) visit(i, m);
	}
}

/** Count list items (ul + ol, all nesting levels) in document order,
 *  ignoring lines inside fenced code blocks. */
export function countChecklistItems(source: string): number {
	let n = 0;
	eachListItem(source, () => { n += 1; });
	return n;
}

/** Toggle the GFM task marker on the Nth (0-based, document order) list
 *  item. A plain item is ticked in one action (`- a` → `- [x] a`); an
 *  item with an existing marker is flipped. The remainder text (including
 *  any user-authored `~~strike~~`) is preserved verbatim. Returns the
 *  source unchanged if `index` is out of range. */
export function toggleChecklistItem(source: string, index: number): string {
	if (index < 0) return source;
	const lines = (source ?? '').split(/\r?\n/);
	let counter = -1;
	let targetLine = -1;
	let targetMatch: RegExpExecArray | null = null;
	eachListItem(source, (lineIndex, match) => {
		counter += 1;
		if (counter === index) { targetLine = lineIndex; targetMatch = match; }
	});
	if (targetLine === -1 || !targetMatch) return source;
	const [, indent, bullet, remainder] = targetMatch as RegExpExecArray;
	const marker = TASK_MARKER_RE.exec(remainder);
	let nextRemainder: string;
	if (marker) {
		const checked = marker[1].toLowerCase() === 'x';
		nextRemainder = `[${checked ? ' ' : 'x'}] ${remainder.slice(marker[0].length)}`;
	} else {
		// Plain item — a tap means "tick it".
		nextRemainder = `[x] ${remainder}`;
	}
	lines[targetLine] = `${indent}${bullet} ${nextRemainder}`;
	return lines.join('\n');
}

/** Checked-state of each list item in document order, derived from the
 *  source markers. Used to drive `decorateChecklist`, because the render
 *  pipeline's DOMPurify pass strips marked's `<input>` checkboxes — so the
 *  rendered DOM no longer carries the checked flag. The marker survives
 *  Smart Markdown token resolution, so reading it from the (resolved)
 *  source the view renders keeps the index mapping intact. */
export function checklistItemStates(source: string): boolean[] {
	const states: boolean[] = [];
	eachListItem(source, (_lineIndex, match) => {
		const marker = TASK_MARKER_RE.exec(match[3]);
		states.push(marker ? marker[1].toLowerCase() === 'x' : false);
	});
	return states;
}

/** Post-render DOM pass (checklist mode only). For each rendered `<li>` in
 *  document order, removes any leftover `<input type=checkbox>` and
 *  prepends an accessible `<button role="checkbox">` carrying a 0-based
 *  `data-checklist-index` that maps back to the source list item. Checked
 *  items get `aria-checked="true"` plus the `md-check-checked` class so CSS
 *  can strike them through. `states` (from `checklistItemStates`) supplies
 *  the checked flags; if omitted, falls back to any surviving input. */
export function decorateChecklist(root: ParentNode, states?: boolean[]): void {
	const items = root.querySelectorAll('li');
	let i = 0;
	for (const li of items) {
		const existing = li.querySelector('input[type="checkbox"]');
		const checked = states
			? Boolean(states[i])
			: existing instanceof HTMLInputElement ? existing.checked : false;
		existing?.remove();
		const btn = (root.ownerDocument ?? document).createElement('button');
		btn.type = 'button';
		btn.className = 'md-check';
		btn.setAttribute('role', 'checkbox');
		btn.setAttribute('aria-checked', checked ? 'true' : 'false');
		btn.setAttribute('data-checklist-index', String(i));
		btn.setAttribute('aria-label', 'Toggle checklist item');
		li.classList.toggle('md-check-checked', checked);
		li.insertBefore(btn, li.firstChild);
		i += 1;
	}
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

	// ADR-137 follow-up: give rendered headings slug ids so the TOC's
	// getElementById jump targets exist. Same slugger as extractHeadings,
	// walked in document order, so ids line up with the TOC entries.
	const slugHeading = makeSlugger();
	for (const h of tpl.content.querySelectorAll('h1, h2, h3, h4, h5, h6')) {
		if (!h.id) h.id = slugHeading(h.textContent ?? '');
	}

	return { html: tpl.innerHTML, links };
}
