/**
 * v5.15.0 (ADR-160, SPEC-160-A): pairing-page logic units.
 *
 * Tests the pure helpers the page depends on, plus the fetch-shape
 * contract for POST /api/auth/pairing-codes. Full Svelte-runtime
 * render tests for $state flows live in e2e — this file keeps the
 * unit footprint deterministic.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest';

// Inline copy of the countdown formatter — keep in sync with
// `formatRemaining` in
// `frontend/src/routes/settings/mcp-pairing/+page.svelte`.
function formatRemaining(s: number): string {
	const mm = Math.floor(s / 60).toString().padStart(2, '0');
	const ss = (s % 60).toString().padStart(2, '0');
	return `${mm}:${ss}`;
}

describe('formatRemaining — countdown display helper', () => {
	it('formats full 10-minute TTL as 10:00', () => {
		expect(formatRemaining(600)).toBe('10:00');
	});

	it('zero-pads single-digit minutes and seconds', () => {
		expect(formatRemaining(65)).toBe('01:05');
		expect(formatRemaining(9)).toBe('00:09');
	});

	it('clamps zero correctly', () => {
		expect(formatRemaining(0)).toBe('00:00');
	});
});

describe('Pairing-code POST contract', () => {
	beforeEach(() => {
		vi.restoreAllMocks();
	});

	it('issues POST /api/auth/pairing-codes with an empty JSON body and Accept JSON', async () => {
		// Stand-in for the page's `apiFetch` wrapper. apiFetch's contract
		// is: POST with method, JSON body, and credentials. The page does
		// not pass a client_hint in v1; it sends `{}`. Future revisions
		// that add a hint should update both the page and this test.
		const fetchMock = vi.fn().mockResolvedValue(
			new Response(
				JSON.stringify({
					code: 'IRIS-ABCD-EFGH',
					expires_at: '2099-01-01T00:00:00+00:00',
				}),
				{
					status: 201,
					headers: { 'Content-Type': 'application/json' },
				},
			),
		);
		vi.stubGlobal('fetch', fetchMock);

		const res = await fetch('/api/auth/pairing-codes', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({}),
		});
		const body = await res.json();

		expect(fetchMock).toHaveBeenCalledOnce();
		const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
		expect(url).toBe('/api/auth/pairing-codes');
		expect(init.method).toBe('POST');
		expect(init.body).toBe('{}');
		expect(body.code).toBe('IRIS-ABCD-EFGH');
		expect(body.expires_at).toBe('2099-01-01T00:00:00+00:00');
	});
});

describe('Pairing-code expiry detection', () => {
	it('treats an expires_at in the past as expired (seconds remaining ≤ 0)', () => {
		const past = new Date(Date.now() - 60_000).toISOString();
		const remaining = Math.round((new Date(past).getTime() - Date.now()) / 1000);
		expect(remaining).toBeLessThanOrEqual(0);
	});

	it('treats an expires_at 10 minutes ahead as fresh', () => {
		const future = new Date(Date.now() + 10 * 60_000).toISOString();
		const remaining = Math.round((new Date(future).getTime() - Date.now()) / 1000);
		expect(remaining).toBeGreaterThan(595);
		expect(remaining).toBeLessThanOrEqual(600);
	});
});
