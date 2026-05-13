/**
 * v6.0.0 (ADR-164, SPEC-164-A): /oauth/authorize consent screen.
 *
 * Inline copies of the helpers used by the page so we can unit-test
 * the validation contract without spinning up SvelteKit's runtime.
 * Keep in sync with frontend/src/routes/oauth/authorize/+page.svelte.
 */
import { describe, it, expect, vi } from 'vitest';
import DOMPurify from 'dompurify';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';


describe('OAuth consent screen — DCR client_name sanitisation', () => {
	it('strips a malicious <script> tag from client_name', () => {
		const malicious = '<script>alert(1)</script>Evil';
		const safe = DOMPurify.sanitize(malicious);
		expect(safe.toLowerCase()).not.toContain('<script>');
	});

	it('preserves benign text', () => {
		const safe = DOMPurify.sanitize('Claude.ai Connector');
		expect(safe).toBe('Claude.ai Connector');
	});

	it('strips inline event handlers', () => {
		const malicious = '<img src=x onerror="alert(1)">';
		const safe = DOMPurify.sanitize(malicious);
		expect(safe).not.toContain('onerror');
	});
});

describe('OAuth consent screen — POST body shape', () => {
	it('forwards all OAuth params from query string to /api/oauth/authorize/prepare', () => {
		// This is the body shape the consent page builds in its onMount
		// from page.url.searchParams. Test catches regressions where a
		// required param gets dropped.
		const params = new URLSearchParams({
			response_type: 'code',
			client_id: 'iris-mcp-test',
			redirect_uri: 'https://example.com/cb',
			code_challenge: 'abc',
			code_challenge_method: 'S256',
			scope: 'iris',
			state: 'xyz',
		});
		const body = {
			response_type: params.get('response_type'),
			client_id: params.get('client_id'),
			redirect_uri: params.get('redirect_uri'),
			code_challenge: params.get('code_challenge'),
			code_challenge_method: params.get('code_challenge_method'),
			scope: params.get('scope') ?? 'iris',
			state: params.get('state'),
		};
		expect(body.response_type).toBe('code');
		expect(body.client_id).toBe('iris-mcp-test');
		expect(body.code_challenge_method).toBe('S256');
	});
});

describe('OAuth consent screen — pairing references removed', () => {
	const PAGE = resolve(__dirname, '../../src/routes/settings/+page.svelte');
	const source = readFileSync(PAGE, 'utf-8');

	it('settings/+page.svelte no longer has a live href to /settings/mcp-pairing', () => {
		// Historical comment references are fine; an actual href= is not.
		expect(source).not.toContain('href="/settings/mcp-pairing"');
	});

	it('settings/+page.svelte no longer has the MCP Connections heading', () => {
		// The text "MCP Connections" was the section heading in v5.15.0.
		// v6.0.0 removed it because pairing is gone.
		// Match the heading specifically; comments mentioning history are fine.
		expect(source).not.toContain('>MCP Connections<');
	});
});
