/**
 * @vitest-environment jsdom
 *
 * Tests for the runMermaidIn runner (ADR-149 / SPEC-149-A).
 *
 * The runner walks .mermaid-block placeholders in a given root
 * element, lazy-imports mermaid, calls mermaid.render() per block,
 * sanitises the SVG via stage-2 DOMPurify, and replaces the
 * placeholder. Errors are caught per-block and rendered as a
 * .mermaid-error element so the rest of the document survives.
 *
 * Lazy-load contract: zero placeholders → zero mermaid imports.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

const mockRender = vi.fn();
const mockInitialize = vi.fn();

vi.mock('mermaid', () => ({
	default: {
		initialize: (...args: unknown[]) => mockInitialize(...args),
		render: (...args: unknown[]) => mockRender(...args),
	},
}));

import { runMermaidIn } from '$lib/components/markdownMermaidRender';

function placeholder(source: string): string {
	const b64 = btoa(unescape(encodeURIComponent(source)));
	return `<pre class="mermaid-block" data-mermaid-source="${b64}"><code>${source}</code></pre>`;
}

function makeRoot(html: string): HTMLDivElement {
	const root = document.createElement('div');
	root.innerHTML = html;
	document.body.appendChild(root);
	return root;
}

beforeEach(() => {
	mockRender.mockReset();
	mockInitialize.mockReset();
	document.body.innerHTML = '';
});

describe('runMermaidIn — happy path', () => {
	it('replaces a placeholder with the rendered SVG', async () => {
		const svg = '<svg xmlns="http://www.w3.org/2000/svg"><g><text>hello</text></g></svg>';
		mockRender.mockResolvedValue({ svg, bindFunctions: undefined });

		const root = makeRoot(placeholder('flowchart TD\nA-->B'));
		await runMermaidIn(root, 'default');

		const block = root.querySelector('.mermaid-block')!;
		expect(block.querySelector('svg')).not.toBeNull();
		expect(block.querySelector('code')).toBeNull();
		expect(mockRender).toHaveBeenCalledTimes(1);
	});

	it('initialises mermaid with the requested theme and securityLevel: "strict"', async () => {
		mockRender.mockResolvedValue({
			svg: '<svg xmlns="http://www.w3.org/2000/svg"></svg>',
			bindFunctions: undefined,
		});

		const root = makeRoot(placeholder('flowchart TD\nA-->B'));
		await runMermaidIn(root, 'dark');

		expect(mockInitialize).toHaveBeenCalled();
		const initArgs = mockInitialize.mock.calls[0][0];
		expect(initArgs.securityLevel).toBe('strict');
		expect(initArgs.theme).toBe('dark');
		expect(initArgs.startOnLoad).toBe(false);
	});

	it('renders multiple placeholders independently with unique ids', async () => {
		const seenIds: string[] = [];
		mockRender.mockImplementation(async (id: string) => {
			seenIds.push(id);
			return { svg: '<svg xmlns="http://www.w3.org/2000/svg"></svg>', bindFunctions: undefined };
		});

		const root = makeRoot(
			placeholder('flowchart TD\nA-->B') +
			'<p>between</p>' +
			placeholder('sequenceDiagram\nX->>Y: hi'),
		);
		await runMermaidIn(root, 'default');

		expect(mockRender).toHaveBeenCalledTimes(2);
		expect(new Set(seenIds).size).toBe(2);
		expect(root.querySelectorAll('.mermaid-block svg').length).toBe(2);
	});
});

describe('runMermaidIn — error fallback', () => {
	it('replaces a failing placeholder with .mermaid-error and leaves the rest of the doc intact', async () => {
		mockRender.mockImplementation(async (_id: string, source: string) => {
			if (source.includes('BROKEN')) throw new Error('Parse error: unexpected token');
			return { svg: '<svg xmlns="http://www.w3.org/2000/svg"><text>ok</text></svg>', bindFunctions: undefined };
		});

		const root = makeRoot(
			placeholder('BROKEN ::: not valid mermaid') +
			'<p data-id="prose">prose</p>' +
			placeholder('flowchart TD\nA-->B'),
		);
		await runMermaidIn(root, 'default');

		const errors = root.querySelectorAll('.mermaid-error');
		expect(errors.length).toBe(1);
		expect(errors[0].textContent).toMatch(/Parse error/);

		expect(root.querySelector('[data-id="prose"]')).not.toBeNull();
		expect(root.querySelectorAll('.mermaid-block svg').length).toBe(1);
	});
});

describe('runMermaidIn — lazy-load contract', () => {
	it('does not import mermaid when there are zero placeholders', async () => {
		const root = makeRoot('<p>plain prose, no diagrams here.</p>');
		await runMermaidIn(root, 'default');
		expect(mockRender).not.toHaveBeenCalled();
		expect(mockInitialize).not.toHaveBeenCalled();
	});
});

describe('runMermaidIn — sanitisation (stage 2)', () => {
	it('strips <script> from mermaid output before injecting', async () => {
		const evilSvg = `
			<svg xmlns="http://www.w3.org/2000/svg">
				<script>window.__pwned_runner = true;</script>
				<g><text>ok</text></g>
			</svg>
		`;
		mockRender.mockResolvedValue({ svg: evilSvg, bindFunctions: undefined });

		const root = makeRoot(placeholder('flowchart TD\nA-->B'));
		await runMermaidIn(root, 'default');

		expect(root.innerHTML).not.toMatch(/<script/i);
		expect((window as unknown as { __pwned_runner?: boolean }).__pwned_runner).toBeUndefined();
	});
});
