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

export interface Element {
	id: string;
	element_type: string;
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
	diagram_usage_count?: number;
	set_id?: string;
	set_name?: string;
	metadata?: Record<string, unknown> | null;
	notation?: string;
}

export interface Diagram {
	id: string;
	diagram_type: string;
	current_version: number;
	name: string;
	description: string | null;
	data: Record<string, unknown>;
	created_at: string;
	created_by: string;
	created_by_username?: string;
	updated_at: string;
	is_deleted: boolean;
	parent_package_id?: string | null;
	tags?: string[];
	set_id?: string;
	set_name?: string;
	notation?: string;
	detected_notations?: string[];
	metadata?: Record<string, unknown> | null;
}

export interface Package {
	id: string;
	current_version: number;
	name: string;
	description: string | null;
	created_at: string;
	created_by: string;
	created_by_username?: string;
	updated_at: string;
	is_deleted: boolean;
	parent_package_id: string | null;
	set_id?: string;
	set_name?: string;
	metadata?: Record<string, unknown> | null;
}

export interface DiagramHierarchyNode {
	id: string;
	name: string;
	node_type: 'package' | 'diagram';
	diagram_type: string | null;
	notation: string | null;
	parent_package_id: string | null;
	has_content: boolean;
	sequence_order: number;
	children: DiagramHierarchyNode[];
}

/** Registry types (ADR-079) */

export interface NotationMapping {
	notation_id: string;
	notation_name: string;
	is_default: boolean;
}

export interface DiagramTypeRegistry {
	id: string;
	name: string;
	description: string | null;
	display_order: number;
	is_active: boolean;
	notations: NotationMapping[];
}

export interface NotationRegistry {
	id: string;
	name: string;
	description: string | null;
	display_order: number;
	is_active: boolean;
}

/** Lock types (ADR-080) */

export interface EditLock {
	id: string;
	target_type: string;
	target_id: string;
	target_name?: string;
	user_id: string;
	username: string;
	acquired_at: string;
	expires_at: string;
	last_heartbeat: string;
}

export interface LockCheckResponse {
	locked: boolean;
	lock: EditLock | null;
	is_owner: boolean;
}

export interface SearchResult {
	id: string;
	result_type: 'element' | 'diagram' | 'package' | 'set' | 'collection';
	name: string;
	description: string | null;
	type_detail: string;
	rank: number;
	deep_link: string;
	set_id: string | null;
	set_name: string | null;
	collection_name: string | null;
	package_name: string | null;
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
	username?: string;
	content: string;
	created_at: string;
	updated_at: string;
}

export interface Bookmark {
	diagram_id: string | null;
	package_id: string | null;
	element_id: string | null;
	created_at: string;
}

export interface PaginatedResponse<T> {
	items: T[];
	total: number;
	page: number;
	page_size: number;
}

export interface ElementVersion {
	element_id: string;
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
	metadata?: Record<string, unknown> | null;
}

export interface DiagramVersion {
	diagram_id: string;
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
	metadata?: Record<string, unknown> | null;
}

export interface Relationship {
	id: string;
	source_element_id: string;
	target_element_id: string;
	relationship_type: string;
	current_version: number;
	label: string | null;
	description: string | null;
	data: Record<string, unknown>;
	created_at: string;
	created_by: string;
	updated_at: string;
	is_deleted: boolean;
	source_element_name?: string;
	target_element_name?: string;
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

export interface ElementDiagramRef {
	diagram_id: string;
	name: string;
	diagram_type: string;
}

export interface ElementStats {
	relationship_count: number;
	diagram_usage_count: number;
}

export interface IrisSet {
	id: string;
	name: string;
	description: string | null;
	created_at: string;
	created_by: string;
	updated_at: string;
	is_deleted: boolean;
	diagram_count: number;
	element_count: number;
	thumbnail_source: 'model' | 'diagram' | 'image' | null;
	thumbnail_diagram_id: string | null;
	has_thumbnail_image: boolean;
	thumbnail_diagram_data?: Record<string, unknown>;
	thumbnail_diagram_type?: string;
	collection_id: string | null;
	collection_name: string | null;
	system_prompt?: string | null;
}

export interface IrisCollection {
	id: string;
	name: string;
	description: string | null;
	created_at: string;
	created_by: string;
	updated_at: string;
	is_deleted: boolean;
	set_count: number;
	diagram_count: number;
	element_count: number;
	thumbnail_source: 'model' | 'diagram' | 'image' | null;
	thumbnail_diagram_id: string | null;
	has_thumbnail_image: boolean;
	thumbnail_diagram_data?: Record<string, unknown>;
	thumbnail_diagram_type?: string;
	system_prompt?: string | null;
}

export interface BatchResult {
	succeeded: number;
	failed: number;
	errors: string[];
}

/** AI provider and Q&A types (ADR-093) */

export interface AIProvider {
	id: string;
	name: string;
	provider_type: string;
	base_url: string | null;
	has_api_key: boolean;
	model: string;
	parameters: Record<string, unknown>;
	system_prompt: string | null;
	timeout_ms: number;
	retries: number;
	is_default: boolean;
	is_active: boolean;
	created_by: string | null;
	created_at: string;
	updated_at: string;
}

export interface QAResponse {
	answer: string;
	model_used: string;
	provider_name: string;
	tokens_in: number | null;
	tokens_out: number | null;
	duration_ms: number;
	conversation_id: string;
}

export interface AIConversation {
	id: string;
	set_id: string;
	question: string;
	answer: string;
	model_used: string;
	provider_id: string | null;
	tokens_in: number | null;
	tokens_out: number | null;
	duration_ms: number | null;
	created_at: string;
	mode: string | null;
	set_name: string | null;
	thread_id: string | null;
}

/** File upload types (ADR-115) */
export interface FileExtractResponse {
	filename: string;
	content_type: string;
	size_bytes: number;
	extracted_text: string;
	truncated: boolean;
	error: string | null;
}

export interface FileContext {
	filename: string;
	text: string;
}

/** Knowledge graph types (ADR-116) */

export interface GraphNode {
	id: string;
	name: string;
	node_type: 'element' | 'diagram' | 'package';
	type_detail: string;
	relationship_count: number;
}

export interface GraphEdge {
	id: string;
	source: string;
	target: string;
	relationship_type: string;
	label: string | null;
	edge_type: string;
}

export interface GraphSettings {
	nodes: Record<string, boolean>;
	edges: Record<string, boolean>;
	label_density: number;
	node_spacing: number;
	size_contrast: number;
	link_length: number;
}

export interface GraphResponse {
	nodes: GraphNode[];
	edges: GraphEdge[];
}

export interface GraphSettingsResponse {
	scope_type: string;
	scope_id: string;
	settings: GraphSettings;
	updated_at: string | null;
	updated_by: string | null;
}

/** @deprecated Use Element instead */
export type Entity = Element;
/** @deprecated Use Diagram instead */
export type Model = Diagram;
/** @deprecated Use DiagramHierarchyNode instead */
export type ModelHierarchyNode = DiagramHierarchyNode;
/** @deprecated Use ElementVersion instead */
export type EntityVersion = ElementVersion;
/** @deprecated Use DiagramVersion instead */
export type ModelVersion = DiagramVersion;
/** @deprecated Use ElementDiagramRef instead */
export type EntityModelRef = ElementDiagramRef;
/** @deprecated Use ElementStats instead */
export type EntityStats = ElementStats;
