/**
 * ADR-154: Multiple named prompts per scope.
 *
 * Mirrors the backend `app/named_prompts/models.py` shapes.
 */

export type ScopeType = 'collection' | 'set';

export interface NamedPrompt {
	id: string;
	scope_type: ScopeType;
	scope_id: string;
	name: string;
	description: string;
	body: string;
	created_at: string;
	updated_at: string;
	created_by: string | null;
}

export interface NamedPromptCreate {
	scope_type: ScopeType;
	scope_id: string;
	name: string;
	description: string;
	body: string;
}

export interface NamedPromptUpdate {
	description?: string;
	body?: string;
}

export interface NamedPromptListResponse {
	items: NamedPrompt[];
}

/**
 * Name validation regex matches the backend model
 * (`app/named_prompts/models.py: NAME_PATTERN`).
 */
export const NAMED_PROMPT_NAME_RE = /^[a-z][a-z0-9-]{0,63}$/;

export const NAMED_PROMPT_DESCRIPTION_MAX = 1024;
export const NAMED_PROMPT_BODY_MAX = 256_000;
