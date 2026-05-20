/**
 * v6.17.3 (issue #194 follow-up): build absolute URLs for image
 * resources served by the Iris API.
 *
 * The frontend (SvelteKit SPA) does not proxy `/api/*` to the backend
 * in production — a relative `<img src="/api/images/<id>">` resolves
 * against the frontend origin, gets the SPA's index.html, and the
 * img tag fails to decode HTML as an image. Prepending API_BASE_URL
 * routes the request to the backend directly.
 *
 * Returns the input unchanged if it isn't an `/api/images/` path
 * (so callers can pass URLs through without inspection).
 */
import { API_BASE_URL } from '$lib/config.js';

const IMAGE_PATH_RE = /^\/api\/images\//;

export function imageUrl(idOrPath: string): string {
	if (!idOrPath) return idOrPath;
	// Already absolute? Pass through.
	if (idOrPath.startsWith('http://') || idOrPath.startsWith('https://')) {
		return idOrPath;
	}
	// Strip leading slash variants and reconstruct.
	const path = idOrPath.startsWith('/api/images/')
		? idOrPath
		: `/api/images/${idOrPath}`;
	return `${API_BASE_URL}${path}`;
}

/**
 * Rewrite any relative `<img src="/api/images/...">` URLs inside an
 * HTML string to absolute backend URLs. Used as a post-DOMPurify
 * pass on Smart Markdown content so resolver-emitted `<img>` tags
 * actually load on production.
 */
export function rewriteImageSrcs(html: string): string {
	if (!html || !API_BASE_URL) return html;
	return html.replace(
		/(<img\b[^>]*\bsrc=)(["'])(\/api\/images\/[^"']+)\2/g,
		(_match, prefix: string, quote: string, path: string) => {
			return `${prefix}${quote}${API_BASE_URL}${path}${quote}`;
		},
	);
}
