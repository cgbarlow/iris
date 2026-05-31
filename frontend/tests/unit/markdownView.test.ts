/**
 * @vitest-environment jsdom
 *
 * Tests target the pure helpers in `markdownHelpers.ts`. The Svelte
 * component is a thin wrapper around these — see ADR-137 / SPEC-137-A.
 */
import { describe, it, expect } from 'vitest';
import {
	renderMarkdown,
	extractHeadings,
	parseIrisHref,
	urlIsAllowed,
} from '$lib/components/markdownHelpers';

describe('renderMarkdown — null/empty input safety (issue #167)', () => {
	it('returns empty html when source is undefined', () => {
		const { html, links } = renderMarkdown(undefined as unknown as string);
		expect(html).toBe('');
		expect(links).toEqual([]);
	});

	it('returns empty html when source is null', () => {
		const { html, links } = renderMarkdown(null as unknown as string);
		expect(html).toBe('');
		expect(links).toEqual([]);
	});

	it('returns empty html when source is the empty string', () => {
		const { html, links } = renderMarkdown('');
		expect(html).toBe('');
		expect(links).toEqual([]);
	});
});

describe('renderMarkdown — sanitisation (protocol #7)', () => {
	it('strips <script> tags from the source', () => {
		const { html } = renderMarkdown('# Heading\n\n<script>window.__pwned = true;</script>\n\nBody.');
		expect(html).not.toMatch(/<script/i);
		expect(html).toContain('Body.');
		expect((window as unknown as { __pwned?: boolean }).__pwned).toBeUndefined();
	});

	it('drops anchors with disallowed URL schemes (javascript:)', () => {
		const { html } = renderMarkdown('[click](javascript:alert(1))\n\n[ok](https://example.com)');
		const tpl = document.createElement('template');
		tpl.innerHTML = html;
		const hrefs = Array.from(tpl.content.querySelectorAll('a')).map(a => a.getAttribute('href'));
		expect(hrefs.some(h => h && h.toLowerCase().startsWith('javascript:'))).toBe(false);
		expect(hrefs).toContain('https://example.com');
	});
});

describe('renderMarkdown — iris:// link rewriting', () => {
	it('extracts iris://diagram and iris://element links and tags anchors', () => {
		const { html, links } = renderMarkdown(
			'See [the diagram](iris://diagram/diag-42) and [an element](iris://element/el-7).'
		);
		expect(links).toEqual([
			{ kind: 'diagram', id: 'diag-42', label: 'the diagram' },
			{ kind: 'element', id: 'el-7',    label: 'an element' },
		]);
		const tpl = document.createElement('template');
		tpl.innerHTML = html;
		const anchors = tpl.content.querySelectorAll('a.md-iris-link');
		expect(anchors.length).toBe(2);
		expect(anchors[0].getAttribute('data-iris-kind')).toBe('diagram');
		expect(anchors[0].getAttribute('data-iris-id')).toBe('diag-42');
		expect(anchors[1].getAttribute('data-iris-kind')).toBe('element');
		expect(anchors[1].getAttribute('data-iris-id')).toBe('el-7');
	});

	it('marks text-class diagram refs with the muted class for grey rendering', () => {
		const { html } = renderMarkdown(
			'[Plain](iris://diagram/d1) and [Text](iris://diagram/d2)',
			new Set(['d2']),
		);
		const tpl = document.createElement('template');
		tpl.innerHTML = html;
		const muted = Array.from(tpl.content.querySelectorAll('a.md-iris-link--text'));
		expect(muted.length).toBe(1);
		expect(muted[0].getAttribute('data-iris-id')).toBe('d2');
	});

	it('does not mark element refs as text-class even if their id matches', () => {
		const { html } = renderMarkdown(
			'[Element](iris://element/d2)',
			new Set(['d2']),
		);
		expect(html).not.toMatch(/md-iris-link--text/);
	});
});

describe('extractHeadings', () => {
	it('extracts headings in source order with depth and slug id', () => {
		const source = [
			'# Top',
			'',
			'## Mid one',
			'',
			'### Deep',
			'',
			'## Mid two',
			'',
			'```',
			'## Inside fence — should be ignored',
			'```',
			'',
			'# Top again',
		].join('\n');

		const headings = extractHeadings(source);
		expect(headings.map(h => [h.level, h.text])).toEqual([
			[1, 'Top'],
			[2, 'Mid one'],
			[3, 'Deep'],
			[2, 'Mid two'],
			[1, 'Top again'],
		]);
		const ids = headings.map(h => h.id);
		expect(new Set(ids).size).toBe(ids.length);
		expect(headings[0].id).toBe('top');
		expect(headings[4].id).toBe('top-again');
	});

	it('returns an empty list when there are no headings', () => {
		expect(extractHeadings('Just paragraphs.')).toEqual([]);
	});

	it('flattens inline markdown (links/emphasis/code) in heading text', () => {
		const source = [
			'## Security (CSE) · [13](iris://diagram/ef1eafcd-e608)',
			'',
			'### **Bold** and `code` and _em_',
		].join('\n');
		const headings = extractHeadings(source);
		expect(headings[0].text).toBe('Security (CSE) · 13');
		expect(headings[0].id).toBe('security-cse-13');
		expect(headings[1].text).toBe('Bold and code and em');
	});
});

describe('renderMarkdown — heading ids match the TOC (ADR-137 follow-up)', () => {
	it('assigns slug ids to rendered headings that match extractHeadings', () => {
		const source = [
			'# Top',
			'',
			'## Security (CSE) · [13](iris://diagram/ef1eafcd-e608)',
		].join('\n');
		const { html } = renderMarkdown(source);
		const tpl = document.createElement('template');
		tpl.innerHTML = html;
		const ids = Array.from(tpl.content.querySelectorAll('h1, h2, h3, h4, h5, h6')).map((h) => h.id);
		const tocIds = extractHeadings(source).map((h) => h.id);
		expect(ids).toEqual(tocIds);
		expect(ids).toContain('security-cse-13');
	});
});

describe('parseIrisHref + urlIsAllowed', () => {
	it('parses iris:// URLs and rejects malformed ones', () => {
		expect(parseIrisHref('iris://diagram/abc')).toEqual({ kind: 'diagram', id: 'abc' });
		expect(parseIrisHref('iris://element/xyz')).toEqual({ kind: 'element', id: 'xyz' });
		expect(parseIrisHref('iris://other/x')).toBeNull();
		expect(parseIrisHref('https://example.com')).toBeNull();
	});

	it('allows http/https/mailto/iris and rejects other schemes', () => {
		expect(urlIsAllowed('https://x.com')).toBe(true);
		expect(urlIsAllowed('http://x.com')).toBe(true);
		expect(urlIsAllowed('mailto:x@y.com')).toBe(true);
		expect(urlIsAllowed('iris://diagram/x')).toBe(true);
		expect(urlIsAllowed('javascript:alert(1)')).toBe(false);
		expect(urlIsAllowed('file:///etc/passwd')).toBe(false);
		expect(urlIsAllowed('data:text/html,<script>1</script>')).toBe(false);
	});
});
