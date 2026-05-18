import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Elements page search race condition (v6.8.5, ADR-196, issue #173 item 7).
 *
 * Bug: the search input fired `loadElements()` synchronously on every
 * keystroke with no debounce and no abort handling. Late responses
 * overwrote recent ones — typing "grocery" showed the matching
 * "Grocery item template source" result, then it flashed away when an
 * earlier in-flight request for "grocer" returned with a different
 * result set.
 *
 * Fix: mirror the dashboard's debounce (300ms) and add an
 * AbortController so later searches cancel earlier in-flight ones.
 * Also discard responses whose query no longer matches the current
 * `searchQuery` as a belt-and-braces guard against the rare case
 * where AbortController fires after a response has already begun
 * resolving in the JS event loop.
 *
 * Static-parser style to match the rest of this suite.
 */

const src = readFileSync(
	resolve(__dirname, '../../src/routes/elements/+page.svelte'),
	'utf-8',
);

describe('Elements page search — debounce', () => {
	it('declares a module-level searchTimeout', () => {
		expect(src).toMatch(/let\s+searchTimeout\s*:\s*ReturnType<typeof setTimeout>/);
	});

	it('declares a debounced onSearchInput handler', () => {
		expect(src).toMatch(/function\s+onSearchInput/);
	});

	it('debounces with setTimeout(..., 300)', () => {
		expect(src).toMatch(/setTimeout\([^,]+,\s*300\)/);
	});

	it('clears the pending timeout on each keystroke', () => {
		expect(src).toMatch(/clearTimeout\(searchTimeout\)/);
	});

	it('search input wires oninput to onSearchInput, not loadElements', () => {
		// The buggy version had `oninput={() => { page = 1; loadElements(); }}`.
		// The fix routes through the debounced handler.
		expect(src).toMatch(/id="element-search"[\s\S]{0,200}?oninput=\{onSearchInput\}/);
	});
});

describe('Elements page search — abort', () => {
	it('declares a module-level AbortController slot', () => {
		expect(src).toMatch(/let\s+loadController\s*:\s*AbortController\s*\|\s*undefined/);
	});

	it('aborts the previous controller at the start of loadElements', () => {
		expect(src).toMatch(/loadController\?\.abort\(\)/);
	});

	it('passes the new controller signal to apiFetch', () => {
		expect(src).toMatch(/apiFetch[^(]*\([^)]*signal[^)]*\)/);
	});

	it('swallows AbortError so it does not surface as a generic load failure', () => {
		expect(src).toMatch(/AbortError/);
	});
});

describe('Elements page search — race guard', () => {
	it('discards stale responses whose query no longer matches', () => {
		// Belt-and-braces: after a debounce window, the in-flight query
		// is captured in a local at fetch-time and compared against the
		// current searchQuery on response.
		expect(src).toMatch(/requestedQuery|searchAtRequest|capturedQuery/);
	});
});
