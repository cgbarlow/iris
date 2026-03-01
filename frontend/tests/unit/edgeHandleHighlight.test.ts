import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Edge endpoint selection highlight CSS tests (WP-13).
 * Verifies that the global stylesheet includes handle hover and
 * edge updater styling rules.
 */

describe('Edge handle highlight CSS', () => {
	const css = readFileSync(resolve(__dirname, '../../src/app.css'), 'utf-8');

	it('includes handle hover styles', () => {
		expect(css).toContain('.svelte-flow__handle:hover');
	});

	it('handle hover has primary colour background', () => {
		// Check that the handle hover rule contains primary colour
		const handleHoverMatch = css.match(
			/\.svelte-flow__handle:hover\s*\{[^}]*background:\s*var\(--color-primary\)/s,
		);
		expect(handleHoverMatch).not.toBeNull();
	});

	it('handle hover has glow effect', () => {
		const handleHoverMatch = css.match(
			/\.svelte-flow__handle:hover\s*\{[^}]*box-shadow:[^}]*var\(--color-primary\)/s,
		);
		expect(handleHoverMatch).not.toBeNull();
	});

	it('includes edgeupdater styles for selected edges', () => {
		expect(css).toContain('.svelte-flow__edgeupdater');
	});

	it('edgeupdater circle uses primary fill', () => {
		const updaterMatch = css.match(
			/\.svelte-flow__edgeupdater\s+circle\s*\{[^}]*fill:\s*var\(--color-primary\)/s,
		);
		expect(updaterMatch).not.toBeNull();
	});

	it('edgeupdater has hover state with larger radius', () => {
		const hoverMatch = css.match(
			/\.svelte-flow__edgeupdater:hover\s+circle\s*\{[^}]*r:\s*10/s,
		);
		expect(hoverMatch).not.toBeNull();
	});
});
