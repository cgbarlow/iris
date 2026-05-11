/**
 * ADR-154 / SPEC-154-A: Named-prompts client wrapper, type shapes,
 * and validation rules. Light-touch unit tests aligned with this
 * repo's frontend testing posture (data shape + business rules,
 * not Svelte component rendering).
 */

import { describe, expect, it } from 'vitest';

import {
	NAMED_PROMPT_BODY_MAX,
	NAMED_PROMPT_DESCRIPTION_MAX,
	NAMED_PROMPT_NAME_RE,
	type NamedPrompt,
	type NamedPromptCreate,
	type NamedPromptListResponse,
} from '$lib/types/named-prompts';

describe('NAMED_PROMPT_NAME_RE', () => {
	it('accepts lowercase-hyphen names', () => {
		for (const name of [
			'a',
			'outcomes-theory',
			'diagram-retrieval',
			'a1',
			'a-1-b-2',
			'a'.repeat(64),
		]) {
			expect(NAMED_PROMPT_NAME_RE.test(name)).toBe(true);
		}
	});

	it('rejects invalid names', () => {
		for (const name of [
			'',
			'1leading-digit',
			'-leading-hyphen',
			'Has-Uppercase',
			'has_underscore',
			'has spaces',
			'a'.repeat(65), // too long
		]) {
			expect(NAMED_PROMPT_NAME_RE.test(name)).toBe(false);
		}
	});
});

describe('Type shape: NamedPrompt', () => {
	it('matches the backend Prompt model fields', () => {
		const p: NamedPrompt = {
			id: 'p-1',
			scope_type: 'set',
			scope_id: 's-1',
			name: 'np',
			description: 'd',
			body: 'b',
			created_at: '2026-05-11T00:00:00Z',
			updated_at: '2026-05-11T00:00:00Z',
			created_by: null,
		};
		expect(p.scope_type).toBe('set');
		expect(p.created_by).toBeNull();
	});

	it('NamedPromptCreate omits server-set fields', () => {
		const body: NamedPromptCreate = {
			scope_type: 'collection',
			scope_id: 'c-1',
			name: 'house-rules',
			description: 'd',
			body: 'b',
		};
		expect(Object.keys(body).sort()).toEqual(
			['body', 'description', 'name', 'scope_id', 'scope_type'],
		);
	});

	it('NamedPromptListResponse wraps an items array', () => {
		const resp: NamedPromptListResponse = { items: [] };
		expect(resp.items).toEqual([]);
	});
});

describe('Validation constants', () => {
	it('description max matches backend', () => {
		expect(NAMED_PROMPT_DESCRIPTION_MAX).toBe(1024);
	});

	it('body max matches backend', () => {
		expect(NAMED_PROMPT_BODY_MAX).toBe(256_000);
	});
});

describe('Effective-prompts inheritance shape', () => {
	it('set-scoped names shadow collection-scoped names', () => {
		// Mirrors the backend logic in
		// app/named_prompts/service.py:list_effective_prompts_for_set
		const own: NamedPrompt[] = [
			{
				id: 'p-set-1', scope_type: 'set', scope_id: 's',
				name: 'overridden', description: 'set version', body: 'set body',
				created_at: 't', updated_at: 't', created_by: null,
			},
		];
		const collectionPrompts: NamedPrompt[] = [
			{
				id: 'p-coll-1', scope_type: 'collection', scope_id: 'c',
				name: 'overridden', description: 'coll version', body: 'coll body',
				created_at: 't', updated_at: 't', created_by: null,
			},
			{
				id: 'p-coll-2', scope_type: 'collection', scope_id: 'c',
				name: 'unique-to-collection', description: 'd', body: 'b',
				created_at: 't', updated_at: 't', created_by: null,
			},
		];

		const ownNames = new Set(own.map((p) => p.name));
		const inherited = collectionPrompts.filter((p) => !ownNames.has(p.name));

		expect(inherited.map((p) => p.name)).toEqual(['unique-to-collection']);
	});
});
