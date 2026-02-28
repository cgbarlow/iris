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
	created_by_username?: string;
	updated_at: string;
	is_deleted: boolean;
	tags?: string[];
	relationship_count?: number;
	model_usage_count?: number;
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
	created_by_username?: string;
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

export interface PaginatedResponse<T> {
	items: T[];
	total: number;
	page: number;
	page_size: number;
}

export interface EntityVersion {
	entity_id: string;
	version: number;
	name: string;
	description: string | null;
	data: Record<string, unknown>;
	change_type: string;
	change_summary: string | null;
	rollback_to: number | null;
	created_at: string;
	created_by: string;
	created_by_username?: string;
}

export interface ModelVersion {
	model_id: string;
	version: number;
	name: string;
	description: string | null;
	data: Record<string, unknown>;
	change_type: string;
	change_summary: string | null;
	rollback_to: number | null;
	created_at: string;
	created_by: string;
	created_by_username?: string;
}

export interface Relationship {
	id: string;
	source_entity_id: string;
	target_entity_id: string;
	relationship_type: string;
	current_version: number;
	label: string | null;
	description: string | null;
	data: Record<string, unknown>;
	created_at: string;
	created_by: string;
	updated_at: string;
	is_deleted: boolean;
}

export interface RelationshipListResponse {
	items: Relationship[];
	total: number;
	page: number;
	page_size: number;
}

export interface AuditEntry {
	id: number;
	timestamp: string;
	user_id: string;
	username: string;
	action: string;
	target_type: string;
	target_id: string | null;
	detail: string | null;
	ip_address: string | null;
	session_id: string | null;
	previous_hash: string;
	entry_hash: string;
}

export interface AuditVerifyResult {
	valid: boolean;
	entries_checked: number;
	verified_at: string;
}

export interface UserDetail {
	id: string;
	username: string;
	role: string;
	is_active: boolean;
	created_at: string;
	last_login_at: string | null;
}

export interface EntityModelRef {
	model_id: string;
	name: string;
	model_type: string;
}

export interface EntityStats {
	relationship_count: number;
	model_usage_count: number;
}
