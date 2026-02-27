/** Core API types shared across the frontend. */

export interface AuthTokens {
	access_token: string;
	refresh_token: string;
	token_type: string;
}

export interface User {
	id: string;
	username: string;
	role: string;
	is_active: boolean;
}

export interface Entity {
	id: string;
	entity_type: string;
	current_version: number;
	name: string;
	description: string | null;
	data: Record<string, unknown>;
	created_at: string;
	created_by: string;
	updated_at: string;
	is_deleted: boolean;
}

export interface Model {
	id: string;
	model_type: string;
	current_version: number;
	name: string;
	description: string | null;
	data: Record<string, unknown>;
	created_at: string;
	created_by: string;
	updated_at: string;
	is_deleted: boolean;
}

export interface SearchResult {
	id: string;
	result_type: 'entity' | 'model';
	name: string;
	description: string | null;
	type_detail: string;
	rank: number;
	deep_link: string;
}

export interface SearchResponse {
	query: string;
	results: SearchResult[];
	total: number;
}

export interface Comment {
	id: string;
	target_type: string;
	target_id: string;
	user_id: string;
	content: string;
	created_at: string;
	updated_at: string;
}

export interface Bookmark {
	model_id: string;
	created_at: string;
}
