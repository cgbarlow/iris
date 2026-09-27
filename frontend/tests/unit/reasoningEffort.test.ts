/**
 * v6.52.0 (ADR-256, SPEC-256-A, #310) — provider reasoning effort.
 */
import { describe, it, expect } from 'vitest';
import { REASONING_EFFORTS, reasoningEffortFromParams } from '$lib/utils/reasoningEffort';

describe('REASONING_EFFORTS', () => {
	it('offers none, low, medium, high in order', () => {
		expect(REASONING_EFFORTS).toEqual(['none', 'low', 'medium', 'high']);
	});
});

describe('reasoningEffortFromParams', () => {
	it('returns the stored value when valid', () => {
		expect(reasoningEffortFromParams({ reasoning_effort: 'none' })).toBe('none');
		expect(reasoningEffortFromParams({ reasoning_effort: 'high' })).toBe('high');
	});

	it('returns blank when unset or unrecognised', () => {
		expect(reasoningEffortFromParams({})).toBe('');
		expect(reasoningEffortFromParams({ reasoning_effort: null })).toBe('');
		expect(reasoningEffortFromParams({ reasoning_effort: 'extreme' })).toBe('');
	});
});
