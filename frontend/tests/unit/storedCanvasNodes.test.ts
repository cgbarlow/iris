/**
 * Issue #315 (ADR-260): turning a diagram's stored nodes into the nodes
 * the canvas renders. Most nodes drop their stored height so Svelte Flow
 * measures them from their content. A boundary is a container, so it
 * keeps the height it was given.
 */
import { describe, it, expect } from 'vitest';
import { storedNodesToCanvas } from '$lib/canvas/storedCanvasNodes';
import type { CanvasNode } from '$lib/types/canvas';

function stored(overrides: Record<string, unknown>): CanvasNode {
	return {
		id: 'n1',
		type: 'component',
		position: { x: 0, y: 0 },
		data: { label: 'A', entityType: 'component' },
		...overrides,
	} as unknown as CanvasNode;
}

describe('storedNodesToCanvas', () => {
	it('drops the stored height and measured size of an ordinary node', () => {
		const [out] = storedNodesToCanvas([
			stored({ width: 180, height: 90, measured: { width: 180, height: 90 } }),
		]);
		expect(out.width).toBe(180);
		expect('height' in out).toBe(false);
		expect('measured' in out).toBe(false);
	});

	it('falls back to visual width, then measured width, then 200', () => {
		const a = stored({ data: { label: 'A', entityType: 'component', visual: { width: 240 } } });
		const b = stored({ measured: { width: 150, height: 40 } });
		const c = stored({});
		expect(storedNodesToCanvas([a, b, c]).map((n) => n.width)).toEqual([240, 150, 200]);
	});

	it('keeps the stored width and height of a boundary', () => {
		const [out] = storedNodesToCanvas([
			stored({
				type: 'boundary',
				width: 520,
				height: 300,
				data: { label: 'Zone', entityType: 'boundary' },
			}),
		]);
		expect(out.width).toBe(520);
		expect(out.height).toBe(300);
	});

	it('recognises a boundary by data.entityType when the node type differs', () => {
		const [out] = storedNodesToCanvas([
			stored({ type: 'default', width: 400, height: 250, data: { label: 'Zone', entityType: 'boundary' } }),
		]);
		expect(out.height).toBe(250);
	});

	it('leaves a boundary without a stored height to size itself', () => {
		const [out] = storedNodesToCanvas([
			stored({ type: 'boundary', width: 300, data: { label: 'Zone', entityType: 'boundary' } }),
		]);
		expect('height' in out).toBe(false);
	});

	it('does not mutate the stored nodes', () => {
		const input = stored({ width: 180, height: 90 });
		storedNodesToCanvas([input]);
		expect(input.height).toBe(90);
	});
});
