// @ts-nocheck
import { describe, it, expect } from 'vitest';
import { isNewerSemver } from '../../src/lib/utils/semverCompare';

describe('isNewerSemver (v5.5.0, issue #48)', () => {
	it('1.0.1 is newer than 1.0.0', () => {
		expect(isNewerSemver('1.0.1', '1.0.0')).toBe(true);
	});
	it('2.0.0 is newer than 1.9.9', () => {
		expect(isNewerSemver('2.0.0', '1.9.9')).toBe(true);
	});
	it('equal versions are not newer', () => {
		expect(isNewerSemver('1.0.0', '1.0.0')).toBe(false);
	});
	it('lower is not newer', () => {
		expect(isNewerSemver('1.0.0', '1.0.1')).toBe(false);
	});
	it('v-prefix is tolerated', () => {
		expect(isNewerSemver('v1.2.0', '1.1.9')).toBe(true);
	});
	it('null / undefined returns false', () => {
		expect(isNewerSemver(null, '1.0.0')).toBe(false);
		expect(isNewerSemver('1.0.0', null)).toBe(false);
		expect(isNewerSemver(undefined, undefined)).toBe(false);
	});
	it('prerelease suffixes are stripped', () => {
		expect(isNewerSemver('2.0.0-rc1', '1.5.0')).toBe(true);
		expect(isNewerSemver('1.0.0-beta', '1.0.0')).toBe(false); // numeric tail equal → not strictly newer
	});
});
