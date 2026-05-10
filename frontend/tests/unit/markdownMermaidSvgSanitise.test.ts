/**
 * @vitest-environment jsdom
 *
 * Stage-2 DOMPurify config tests (ADR-149 / SPEC-149-A).
 *
 * The runner sanitises mermaid's output SVG before injecting it into
 * the page. The config must:
 *   - preserve standard svg tags (svg/g/path/rect/text/marker/defs),
 *   - preserve the explicit foreignObject add (mermaid HTML labels),
 *   - strip <script>, inline event handlers, and javascript: URLs
 *     even when they appear inside foreignObject.
 */
import { describe, it, expect } from 'vitest';
import { sanitiseMermaidSvg } from '$lib/components/markdownMermaidRender';

describe('sanitiseMermaidSvg — preserved tags', () => {
	it('preserves a representative mermaid SVG output', () => {
		const svg = `
			<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
				<defs>
					<marker id="arrow" markerWidth="10" markerHeight="10" refX="0" refY="3"
						orient="auto" markerUnits="strokeWidth">
						<path d="M0,0 L0,6 L9,3 z" />
					</marker>
				</defs>
				<g class="node">
					<rect x="0" y="0" width="50" height="20" />
					<text x="25" y="10" text-anchor="middle">A</text>
				</g>
				<g class="edgePath">
					<path d="M50,10 L80,10" marker-end="url(#arrow)" />
				</g>
			</svg>
		`;

		const safe = sanitiseMermaidSvg(svg);
		expect(safe).toMatch(/<svg/i);
		expect(safe).toMatch(/<defs/i);
		expect(safe).toMatch(/<marker/i);
		expect(safe).toMatch(/<g/i);
		expect(safe).toMatch(/<rect/i);
		expect(safe).toMatch(/<text/i);
		expect(safe).toMatch(/<path/i);
	});

	it('preserves <foreignObject> for mermaid HTML labels', () => {
		const svg = `
			<svg xmlns="http://www.w3.org/2000/svg">
				<foreignObject x="0" y="0" width="100" height="40">
					<div xmlns="http://www.w3.org/1999/xhtml">Label text</div>
				</foreignObject>
			</svg>
		`;

		const safe = sanitiseMermaidSvg(svg);
		expect(safe).toMatch(/<foreignObject/i);
		expect(safe).toContain('Label text');
	});
});

describe('sanitiseMermaidSvg — stripped attack vectors', () => {
	it('strips <script> tags inside the SVG', () => {
		const svg = `
			<svg xmlns="http://www.w3.org/2000/svg">
				<script>window.__pwned_svg = true;</script>
				<g><text>ok</text></g>
			</svg>
		`;
		const safe = sanitiseMermaidSvg(svg);
		expect(safe).not.toMatch(/<script/i);
		expect((window as unknown as { __pwned_svg?: boolean }).__pwned_svg).toBeUndefined();
	});

	it('strips inline event handlers (onload, onclick, onerror)', () => {
		const svg = `
			<svg xmlns="http://www.w3.org/2000/svg" onload="alert('x')">
				<rect onclick="alert('y')" />
				<image href="x.png" onerror="alert('z')" />
			</svg>
		`;
		const safe = sanitiseMermaidSvg(svg);
		expect(safe).not.toMatch(/onload=/i);
		expect(safe).not.toMatch(/onclick=/i);
		expect(safe).not.toMatch(/onerror=/i);
	});

	it('strips <script> and event handlers inside <foreignObject>', () => {
		const svg = `
			<svg xmlns="http://www.w3.org/2000/svg">
				<foreignObject>
					<div xmlns="http://www.w3.org/1999/xhtml">
						<script>window.__pwned_fo = true;</script>
						<a href="javascript:alert(1)">click</a>
						<img src="x" onerror="window.__pwned_fo = true" />
					</div>
				</foreignObject>
			</svg>
		`;
		const safe = sanitiseMermaidSvg(svg);
		expect(safe).not.toMatch(/<script/i);
		expect(safe).not.toMatch(/javascript:/i);
		expect(safe).not.toMatch(/onerror=/i);
		expect((window as unknown as { __pwned_fo?: boolean }).__pwned_fo).toBeUndefined();
	});
});
