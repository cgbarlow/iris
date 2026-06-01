/**
 * ADR-230 F2 / SPEC-230-A AC2: nodeOverrideStyle emits a corner radius
 * from NodeVisualOverrides (borderRadius / cornerStyle) so EA-styled and
 * GEANZ nodes can be rounded or pill-shaped without a theme-schema change.
 */

import { describe, expect, it } from 'vitest';

import { nodeOverrideStyle } from '$lib/canvas/utils/visualStyles';

describe('nodeOverrideStyle border radius (ADR-230 F2)', () => {
	it('emits a pill radius for cornerStyle: pill', () => {
		expect(nodeOverrideStyle({ cornerStyle: 'pill' })).toContain('border-radius: 9999px');
	});

	it('emits 0 radius for cornerStyle: sharp', () => {
		expect(nodeOverrideStyle({ cornerStyle: 'sharp' })).toContain('border-radius: 0');
	});

	it('emits an explicit px radius for borderRadius', () => {
		expect(nodeOverrideStyle({ borderRadius: 14 })).toContain('border-radius: 14px');
	});

	it('lets cornerStyle: pill win over an explicit borderRadius', () => {
		const style = nodeOverrideStyle({ cornerStyle: 'pill', borderRadius: 10 });
		expect(style).toContain('border-radius: 9999px');
		expect(style).not.toContain('border-radius: 10px');
	});

	it('emits no border-radius when neither is set (back-compat)', () => {
		expect(nodeOverrideStyle({ bgColor: '#ccf2fe' })).not.toContain('border-radius');
	});

	it('still carries the GEANZ zone fill + border + dashed style', () => {
		const style = nodeOverrideStyle({
			bgColor: '#ccf2fe',
			borderColor: '#4169e1',
			borderWidth: 3,
			borderStyle: 'solid',
			borderRadius: 14,
		});
		expect(style).toContain('background-color: #ccf2fe');
		expect(style).toContain('border-color: #4169e1');
		expect(style).toContain('border-width: 3px');
		expect(style).toContain('border-radius: 14px');
	});
});
