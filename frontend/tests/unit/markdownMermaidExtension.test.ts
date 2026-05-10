/**
 * @vitest-environment jsdom
 *
 * Tests for the marked mermaid extension (ADR-149 / SPEC-149-A).
 *
 * The extension intercepts ```mermaid fenced blocks and emits a
 * placeholder <pre class="mermaid-block" data-mermaid-source="<base64>">.
 * The placeholder must:
 *   - survive stage-1 DOMPurify with default config,
 *   - round-trip the source via base64 in the data attribute,
 *   - leave non-mermaid fenced blocks untouched (regression guard),
 *   - not pull the mermaid bundle into the synchronous render path
 *     (lazy-load contract — verified via vi.mock).
 */
import { describe, it, expect, vi } from 'vitest';

// Lazy-load contract: importing `markdownHelpers` (and therefore the
// mermaid extension at module scope) must NOT pull in the mermaid
// library. Mock it to throw if anything reaches it during the
// markdown pipeline.
vi.mock('mermaid', () => {
	throw new Error('mermaid bundle imported during markdown render — lazy-load contract violated');
});

import { renderMarkdown } from '$lib/components/markdownHelpers';

function decodeSource(b64: string): string {
	// jsdom provides atob
	return decodeURIComponent(escape(atob(b64)));
}

describe('markdown mermaid extension — placeholder shape', () => {
	it('emits a <pre class="mermaid-block"> with the source base64-encoded in data-mermaid-source', () => {
		const source = '```mermaid\nflowchart TD\nA-->B\n```\n';
		const { html } = renderMarkdown(source);

		const tpl = document.createElement('template');
		tpl.innerHTML = html;
		const block = tpl.content.querySelector('pre.mermaid-block');
		expect(block).not.toBeNull();

		const b64 = block!.getAttribute('data-mermaid-source');
		expect(b64).toBeTruthy();
		expect(decodeSource(b64!)).toBe('flowchart TD\nA-->B');
	});

	it('preserves a human-readable <code> child so search/select-copy still works before mermaid runs', () => {
		const { html } = renderMarkdown('```mermaid\ngraph LR\nX-->Y\n```\n');
		const tpl = document.createElement('template');
		tpl.innerHTML = html;
		const code = tpl.content.querySelector('pre.mermaid-block code');
		expect(code).not.toBeNull();
		expect(code!.textContent).toContain('graph LR');
		expect(code!.textContent).toContain('X-->Y');
	});

	it('round-trips multi-line source with special characters via base64', () => {
		const source = [
			'```mermaid',
			'sequenceDiagram',
			'  Alice->>Bob: "Hello, & welcome!"',
			'  Bob-->>Alice: <reply>',
			'```',
		].join('\n');

		const { html } = renderMarkdown(source);
		const tpl = document.createElement('template');
		tpl.innerHTML = html;
		const block = tpl.content.querySelector('pre.mermaid-block');
		const decoded = decodeSource(block!.getAttribute('data-mermaid-source')!);
		expect(decoded).toBe([
			'sequenceDiagram',
			'  Alice->>Bob: "Hello, & welcome!"',
			'  Bob-->>Alice: <reply>',
		].join('\n'));
	});
});

describe('markdown mermaid extension — non-mermaid fences untouched (regression guard)', () => {
	it('leaves ```typescript blocks as ordinary code blocks', () => {
		const { html } = renderMarkdown('```typescript\nconst x = 1;\n```\n');
		expect(html).not.toMatch(/mermaid-block/);
		expect(html).toMatch(/<pre>/);
		expect(html).toMatch(/<code/);
		expect(html).toContain('const x = 1');
	});

	it('leaves un-tagged ``` blocks as ordinary code blocks', () => {
		const { html } = renderMarkdown('```\njust plain text\n```\n');
		expect(html).not.toMatch(/mermaid-block/);
		expect(html).toContain('just plain text');
	});

	it('does not match a fence whose info-string only starts with "mermaid"', () => {
		// "mermaid-extra" must not be treated as mermaid — the info-string
		// match is exact (case-insensitive), not prefix.
		const { html } = renderMarkdown('```mermaid-extra\ncontent\n```\n');
		expect(html).not.toMatch(/mermaid-block/);
	});
});

describe('markdown mermaid extension — mixed content', () => {
	it('handles a mermaid block followed by a paragraph followed by another mermaid block', () => {
		const source = [
			'# Title',
			'',
			'```mermaid',
			'flowchart TD',
			'A-->B',
			'```',
			'',
			'Some prose between diagrams.',
			'',
			'```mermaid',
			'sequenceDiagram',
			'X->>Y: hello',
			'```',
		].join('\n');

		const { html } = renderMarkdown(source);
		const tpl = document.createElement('template');
		tpl.innerHTML = html;

		const blocks = tpl.content.querySelectorAll('pre.mermaid-block');
		expect(blocks.length).toBe(2);
		expect(decodeSource(blocks[0].getAttribute('data-mermaid-source')!)).toContain('flowchart TD');
		expect(decodeSource(blocks[1].getAttribute('data-mermaid-source')!)).toContain('sequenceDiagram');
		expect(html).toContain('Some prose between diagrams.');
	});
});
