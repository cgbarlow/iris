/**
 * v5.17.0 (ADR-162) — /login honours a same-origin `?redirect=`
 * query param after sign-in, so signing in from /settings/mcp-pairing
 * returns the user there, not to the dashboard. Same-origin paths
 * only — external/protocol redirects rejected to /.
 *
 * Inline copy of `safeRedirectTarget` so we can unit-test the
 * validation without spinning up SvelteKit's $app/state. Keep in
 * sync with `frontend/src/routes/login/+page.svelte`.
 */
import { describe, it, expect } from 'vitest';

function safeRedirectTarget(redirect: string | null): string {
	if (!redirect) return '/';
	if (!redirect.startsWith('/')) return '/';
	if (redirect.startsWith('//')) return '/';
	if (redirect.includes('://')) return '/';
	if (/\s/.test(redirect)) return '/';
	return redirect;
}

describe('safeRedirectTarget — login redirect-back validation', () => {
	it('returns / when no redirect provided', () => {
		expect(safeRedirectTarget(null)).toBe('/');
	});

	it('honours a same-origin path', () => {
		expect(safeRedirectTarget('/settings/mcp-pairing')).toBe('/settings/mcp-pairing');
	});

	it('honours a deeper same-origin path with query', () => {
		expect(safeRedirectTarget('/admin/users?role=admin')).toBe('/admin/users?role=admin');
	});

	it('rejects protocol-relative URLs (//evil.example)', () => {
		expect(safeRedirectTarget('//evil.example/path')).toBe('/');
	});

	it('rejects absolute URLs with scheme', () => {
		expect(safeRedirectTarget('https://evil.example/path')).toBe('/');
		expect(safeRedirectTarget('http://evil.example')).toBe('/');
		expect(safeRedirectTarget('javascript://alert(1)')).toBe('/');
	});

	it('rejects paths not starting with /', () => {
		expect(safeRedirectTarget('settings/mcp-pairing')).toBe('/');
		expect(safeRedirectTarget('../etc/passwd')).toBe('/');
	});

	it('rejects paths containing whitespace', () => {
		expect(safeRedirectTarget('/path with space')).toBe('/');
		expect(safeRedirectTarget('/path\twith\ttab')).toBe('/');
	});
});
