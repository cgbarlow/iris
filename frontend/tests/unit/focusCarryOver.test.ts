/**
 * v6.52.2 (ADR-258) — following a link to another view while in full screen
 * (focus mode) keeps the next view in full screen.
 */
import { describe, it, expect } from 'vitest';
import { focusCarryOverTarget } from '$lib/utils/focusCarryOver';

const u = (s: string) => new URL(s, 'https://iris.test');

describe('focusCarryOverTarget', () => {
	it('adds focus=1 when leaving a focused view for another view', () => {
		expect(focusCarryOverTarget(true, u('/views/a?focus=1'), u('/views/b'), 'link')).toBe('/views/b?focus=1');
	});

	it('works for goto navigations (linked-diagram nodes) and keeps other params and hash', () => {
		expect(focusCarryOverTarget(true, u('/views/a?focus=1'), u('/views/b?x=1#n'), 'goto')).toBe('/views/b?x=1&focus=1#n');
	});

	it('does nothing when not in focus mode', () => {
		expect(focusCarryOverTarget(false, u('/views/a'), u('/views/b'), 'link')).toBeNull();
	});

	it('does nothing when the target already has focus=1', () => {
		expect(focusCarryOverTarget(true, u('/views/a?focus=1'), u('/views/b?focus=1'), 'link')).toBeNull();
	});

	it('does nothing for the same view (entering/exiting focus rewrites its own URL)', () => {
		expect(focusCarryOverTarget(true, u('/views/a?focus=1'), u('/views/a'), 'goto')).toBeNull();
	});

	it('does nothing for non-view targets', () => {
		expect(focusCarryOverTarget(true, u('/views/a?focus=1'), u('/elements/e'), 'link')).toBeNull();
		expect(focusCarryOverTarget(true, u('/views/a?focus=1'), u('/views'), 'link')).toBeNull();
	});

	it('does nothing for back/forward, external or missing targets', () => {
		expect(focusCarryOverTarget(true, u('/views/a?focus=1'), u('/views/b'), 'popstate')).toBeNull();
		expect(focusCarryOverTarget(true, u('/views/a?focus=1'), null, 'leave')).toBeNull();
		expect(focusCarryOverTarget(true, u('/views/a?focus=1'), new URL('https://other.test/views/b'), 'link')).toBeNull();
	});
});
