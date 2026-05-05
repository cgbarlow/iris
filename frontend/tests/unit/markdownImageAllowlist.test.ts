// @ts-nocheck — vitest's jsdom env handles DOMPurify here.
/**
 * @vitest-environment jsdom
 *
 * Issue #32 reopen — User Guide images stopped loading after v5.1.0
 * because the shared MarkdownView's `ALLOWED_URI_REGEXP` requires a
 * scheme (`https?`/`mailto`/`iris`). `<img src="/guide/foo.png">` has
 * no scheme, so DOMPurify stripped the src.
 *
 * v5.3.0 widens the regex to also accept absolute (`/`) and relative
 * (`./`, `../`) paths. The post-walk `urlIsAllowed` already handles
 * those correctly via `new URL(href, placeholder)`.
 *
 * This test asserts that the new regex accepts the path patterns the
 * User Guide actually uses while still rejecting `javascript:`,
 * `data:`, `file:`, `about:`.
 */
import { describe, it, expect } from 'vitest';
import { renderMarkdown } from '$lib/components/markdownHelpers';

function imgSrc(html: string): string | null {
	const tpl = document.createElement('template');
	tpl.innerHTML = html;
	return tpl.content.querySelector('img')?.getAttribute('src') ?? null;
}

function anchorHref(html: string): string | null {
	const tpl = document.createElement('template');
	tpl.innerHTML = html;
	return tpl.content.querySelector('a')?.getAttribute('href') ?? null;
}

describe('Markdown image / link allowlist (issue #32 reopen)', () => {
	it('preserves absolute-path image src (the User Guide pattern)', () => {
		const { html } = renderMarkdown('![dashboard](/guide/dashboard.png)');
		expect(imgSrc(html)).toBe('/guide/dashboard.png');
	});

	it('preserves relative-path image src', () => {
		const { html } = renderMarkdown('![rel](./foo.png)');
		expect(imgSrc(html)).toBe('./foo.png');
	});

	it('preserves https:// image src', () => {
		const { html } = renderMarkdown('![ext](https://example.com/x.png)');
		expect(imgSrc(html)).toBe('https://example.com/x.png');
	});

	it('strips javascript: image src (defence in depth)', () => {
		const { html } = renderMarkdown('![bad](javascript:alert(1))');
		const src = imgSrc(html);
		expect(src === null || !/^javascript:/i.test(src)).toBe(true);
	});

	it('strips data: image src', () => {
		const { html } = renderMarkdown('![bad](data:text/html,<script>1</script>)');
		const src = imgSrc(html);
		expect(src === null || !/^data:/i.test(src)).toBe(true);
	});

	it('strips file: image src', () => {
		const { html } = renderMarkdown('![bad](file:///etc/passwd)');
		const src = imgSrc(html);
		expect(src === null || !/^file:/i.test(src)).toBe(true);
	});

	it('preserves absolute-path anchor href', () => {
		const { html } = renderMarkdown('[tab](/views/123)');
		expect(anchorHref(html)).toBe('/views/123');
	});

	it('preserves iris:// anchor href', () => {
		const { html } = renderMarkdown('[link](iris://diagram/abc)');
		expect(anchorHref(html)).toBe('iris://diagram/abc');
	});

	it('strips javascript: anchor href (regression guard)', () => {
		const { html } = renderMarkdown('[bad](javascript:alert(1))');
		const href = anchorHref(html);
		expect(href === null || !/^javascript:/i.test(href)).toBe(true);
	});
});
