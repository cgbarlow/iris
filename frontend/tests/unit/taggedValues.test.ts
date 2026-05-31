/**
 * ADR-228 / SPEC-228-A: Sparx EA `#NOTES#` tagged-value helpers.
 *
 * Pure-function tests covering the split / join / unset checks used
 * by the element metadata editor and (eventually) any other caller
 * that needs to parse Sparx tagged-value strings on the frontend.
 */

import { describe, expect, it } from 'vitest';

import {
	isUnsetTaggedValue,
	joinTaggedValue,
	splitTaggedValue,
} from '$lib/utils/taggedValues';

describe('splitTaggedValue', () => {
	it('returns the raw value when no #NOTES# marker is present', () => {
		expect(splitTaggedValue('3')).toEqual({ value: '3', notes: '' });
		expect(splitTaggedValue('Approved')).toEqual({ value: 'Approved', notes: '' });
	});

	it('splits value from notes on the #NOTES# marker', () => {
		expect(splitTaggedValue('3#NOTES#Values: 1,2,3')).toEqual({
			value: '3',
			notes: 'Values: 1,2,3',
		});
	});

	it('handles multi-line notes (Sparx convention)', () => {
		const raw =
			'-#NOTES#Values: -,0,1,2,3,4,5\nDefault: -\nDescription: 0 - Does not exist';
		expect(splitTaggedValue(raw)).toEqual({
			value: '-',
			notes: 'Values: -,0,1,2,3,4,5\nDefault: -\nDescription: 0 - Does not exist',
		});
	});

	it('returns empty value and notes for unset placeholders', () => {
		expect(splitTaggedValue(null)).toEqual({ value: '', notes: '' });
		expect(splitTaggedValue(undefined)).toEqual({ value: '', notes: '' });
		expect(splitTaggedValue('')).toEqual({ value: '', notes: '' });
		expect(splitTaggedValue('-')).toEqual({ value: '', notes: '' });
	});

	it('treats a #NOTES# at the very start as empty value + everything as notes', () => {
		expect(splitTaggedValue('#NOTES#just a description')).toEqual({
			value: '',
			notes: 'just a description',
		});
	});
});

describe('joinTaggedValue', () => {
	it('omits the #NOTES# marker when notes is empty', () => {
		expect(joinTaggedValue('3', '')).toBe('3');
		expect(joinTaggedValue('Approved', '')).toBe('Approved');
	});

	it('joins value and notes with #NOTES#', () => {
		expect(joinTaggedValue('3', 'Values: 1,2,3')).toBe('3#NOTES#Values: 1,2,3');
	});

	it('preserves multi-line notes verbatim', () => {
		const notes = 'Values: -,0,1,2,3,4,5\nDefault: -\nDescription: …';
		expect(joinTaggedValue('-', notes)).toBe(`-#NOTES#${notes}`);
	});
});

describe('round-trip', () => {
	it('join(split(x)) === x for any non-unset value', () => {
		const cases = [
			'3',
			'3#NOTES#Values: 1,2,3',
			'Approved',
			'-#NOTES#Values: -,0,1,2,3\nDefault: -',
			'#NOTES#description only',
		];
		for (const x of cases) {
			const { value, notes } = splitTaggedValue(x);
			expect(joinTaggedValue(value, notes)).toBe(x);
		}
	});
});

describe('isUnsetTaggedValue', () => {
	it.each([null, undefined, '', '-', '-#NOTES#Values: 1,2,3'])(
		'treats %p as unset',
		(v) => {
			expect(isUnsetTaggedValue(v)).toBe(true);
		},
	);

	it.each(['3', '3#NOTES#desc', 'Approved', '0', 'false'])(
		'treats %p as set',
		(v) => {
			expect(isUnsetTaggedValue(v)).toBe(false);
		},
	);
});
