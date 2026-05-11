/**
 * ADR-154 / SPEC-154-A: typed client for `/api/named-prompts*`.
 *
 * Thin wrappers around the shared `apiFetch` helper. Sanitisation
 * happens at the call site (matching the pattern used for
 * collections / sets) — keep these wrappers focused on transport.
 */

import { apiFetch } from '$lib/utils/api';
import type {
	NamedPrompt,
	NamedPromptCreate,
	NamedPromptListResponse,
	NamedPromptUpdate,
	ScopeType,
} from '$lib/types/named-prompts';

export async function listNamedPromptsForScope(
	scope_type: ScopeType,
	scope_id: string,
): Promise<NamedPrompt[]> {
	const params = new URLSearchParams({ scope_type, scope_id });
	const resp = await apiFetch<NamedPromptListResponse>(`/api/named-prompts?${params}`);
	return resp.items;
}

export async function listEffectiveNamedPromptsForSet(
	set_id: string,
): Promise<NamedPrompt[]> {
	const params = new URLSearchParams({ set_id });
	const resp = await apiFetch<NamedPromptListResponse>(`/api/named-prompts/by-scope?${params}`);
	return resp.items;
}

export async function listEffectiveNamedPromptsForCollection(
	collection_id: string,
): Promise<NamedPrompt[]> {
	const params = new URLSearchParams({ collection_id });
	const resp = await apiFetch<NamedPromptListResponse>(`/api/named-prompts/by-scope?${params}`);
	return resp.items;
}

export async function createNamedPrompt(body: NamedPromptCreate): Promise<NamedPrompt> {
	return apiFetch<NamedPrompt>('/api/named-prompts', {
		method: 'POST',
		body: JSON.stringify(body),
	});
}

export async function updateNamedPrompt(
	id: string,
	body: NamedPromptUpdate,
): Promise<NamedPrompt> {
	return apiFetch<NamedPrompt>(`/api/named-prompts/${id}`, {
		method: 'PUT',
		body: JSON.stringify(body),
	});
}

export async function deleteNamedPrompt(id: string): Promise<void> {
	await apiFetch<void>(`/api/named-prompts/${id}`, { method: 'DELETE' });
}
