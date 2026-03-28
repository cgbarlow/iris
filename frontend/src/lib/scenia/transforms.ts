/**
 * Bidirectional transforms between Iris API shapes and Scenia native types.
 *
 * Iris stores Scenia entities as elements with name/description pulled out
 * and all other fields packed into a JSON `data` blob.
 * Scenia expects all fields as top-level properties on each entity.
 */

// --- Iris API types (what the backend returns) ---

export interface SceniaEntity {
	id: string;
	element_type: string;
	name: string;
	description: string | null;
	data: Record<string, unknown>;
	set_id: string | null;
	created_at: string;
	updated_at: string;
}

export interface SceniaDependency {
	id: string;
	source_id: string;
	target_id: string;
	dependency_type: string;
	set_id: string | null;
	data: Record<string, unknown>;
	created_at: string;
}

export interface IrisAssetCategory {
	id: string;
	set_id: string;
	name: string;
	color: string | null;
	display_order: number;
}

export interface IrisAppStatus {
	id: string;
	set_id: string;
	name: string;
	color: string | null;
	display_order: number;
}

export interface IrisTimelineSettings {
	id: string;
	set_id: string;
	start_date: string | null;
	end_date: string | null;
	view_mode: string;
	zoom_level: number;
	data: Record<string, unknown>;
	updated_at: string;
}

export interface VersionSnapshot {
	id: string;
	set_id: string;
	version_number: number;
	name: string | null;
	data: Record<string, unknown>;
	created_at: string;
	created_by: string;
}

export interface SceniaBulkData {
	strategies: SceniaEntity[];
	programmes: SceniaEntity[];
	initiatives: SceniaEntity[];
	assets: SceniaEntity[];
	applications: SceniaEntity[];
	app_segments: SceniaEntity[];
	milestones: SceniaEntity[];
	resources: SceniaEntity[];
	dependencies: SceniaDependency[];
	asset_categories: IrisAssetCategory[];
	app_statuses: IrisAppStatus[];
	timeline_settings: IrisTimelineSettings | null;
	versions: VersionSnapshot[];
}

// --- Scenia native types (what the React app expects) ---
// These match the interfaces in scenia/src/types.ts

interface SceniaNativeAppData {
	strategies: Array<{ id: string; name: string; color: string }>;
	programmes: Array<{ id: string; name: string; color: string }>;
	initiatives: Array<Record<string, unknown>>;
	assets: Array<Record<string, unknown>>;
	applications: Array<{ id: string; assetId: string; name: string }>;
	applicationSegments: Array<Record<string, unknown>>;
	milestones: Array<Record<string, unknown>>;
	resources: Array<{ id: string; name: string; role?: string }>;
	dependencies: Array<{ id: string; sourceId: string; targetId: string; type: string; [k: string]: unknown }>;
	assetCategories: Array<{ id: string; name: string; order?: number }>;
	timelineSettings: Record<string, unknown>;
	applicationStatuses: Array<{ id: string; name: string; color: string }>;
}

/**
 * Convert an Iris SceniaEntity to a Scenia native object.
 * Unpacks the `data` blob and merges with id/name/description.
 */
function entityToNative(entity: SceniaEntity): Record<string, unknown> {
	return {
		id: entity.id,
		name: entity.name,
		...(entity.description != null ? { description: entity.description } : {}),
		...(entity.data ?? {}),
	};
}

/**
 * Convert a Scenia native object back to Iris API create shape.
 * Packs all fields except id/name/description into `data`.
 */
function nativeToEntity(
	native: Record<string, unknown>,
	setId: string,
): { id?: string; name: string; description: string | null; data: Record<string, unknown>; set_id: string } {
	const { id, name, description, ...rest } = native;
	return {
		...(id != null ? { id: String(id) } : {}),
		name: (name as string) ?? 'Untitled',
		description: (description as string) ?? null,
		data: rest,
		set_id: setId,
	};
}

/**
 * Transform Iris API bulk response → Scenia native AppData.
 */
export function apiToScenia(apiData: SceniaBulkData): SceniaNativeAppData {
	return {
		strategies: apiData.strategies.map(entityToNative) as SceniaNativeAppData['strategies'],
		programmes: apiData.programmes.map(entityToNative) as SceniaNativeAppData['programmes'],
		initiatives: apiData.initiatives.map(entityToNative),
		assets: apiData.assets.map(entityToNative),
		applications: apiData.applications.map(entityToNative) as SceniaNativeAppData['applications'],
		applicationSegments: apiData.app_segments.map(entityToNative),
		milestones: apiData.milestones.map(entityToNative),
		resources: apiData.resources.map(entityToNative) as SceniaNativeAppData['resources'],
		dependencies: apiData.dependencies.map((dep) => ({
			id: dep.id,
			sourceId: dep.source_id,
			targetId: dep.target_id,
			type: dep.dependency_type,
			...dep.data,
		})),
		assetCategories: apiData.asset_categories.map((cat) => ({
			id: cat.id,
			name: cat.name,
			order: cat.display_order,
		})),
		timelineSettings: apiData.timeline_settings
			? { ...apiData.timeline_settings.data, startDate: apiData.timeline_settings.start_date }
			: { startDate: `${new Date().getFullYear()}-01-01`, monthsToShow: 36 },
		applicationStatuses: apiData.app_statuses.map((s) => ({
			id: s.id,
			name: s.name,
			color: s.color ?? '#6b7280',
		})),
	};
}

/**
 * Transform Scenia native save data → Iris API write payload.
 */
export function sceniaToApi(
	sceniaData: Record<string, unknown>,
	setId: string,
): Record<string, unknown> {
	const data = sceniaData as Partial<SceniaNativeAppData>;
	const result: Record<string, unknown> = {};

	const entityKeys: Array<[string, string]> = [
		['strategies', 'strategies'],
		['programmes', 'programmes'],
		['initiatives', 'initiatives'],
		['assets', 'assets'],
		['applications', 'applications'],
		['applicationSegments', 'app_segments'],
		['milestones', 'milestones'],
		['resources', 'resources'],
	];

	for (const [nativeKey, apiKey] of entityKeys) {
		const items = data[nativeKey as keyof SceniaNativeAppData];
		if (Array.isArray(items)) {
			result[apiKey] = items.map((item) => nativeToEntity(item as Record<string, unknown>, setId));
		}
	}

	if (data.dependencies) {
		result.dependencies = data.dependencies.map((dep) => {
			const { id, sourceId, targetId, type, ...rest } = dep;
			return {
				...(id != null ? { id: String(id) } : {}),
				source_id: sourceId,
				target_id: targetId,
				dependency_type: type,
				set_id: setId,
				data: rest,
			};
		});
	}

	if (data.assetCategories) {
		result.asset_categories = data.assetCategories.map((cat) => ({
			...(cat.id != null ? { id: String(cat.id) } : {}),
			name: cat.name,
			display_order: cat.order ?? 0,
			set_id: setId,
		}));
	}

	if (data.applicationStatuses) {
		result.app_statuses = data.applicationStatuses.map((s) => ({
			...(s.id != null ? { id: String(s.id) } : {}),
			name: s.name,
			color: s.color,
			display_order: 0,
			set_id: setId,
		}));
	}

	if (data.timelineSettings) {
		const ts = data.timelineSettings as Record<string, unknown>;
		const { startDate, monthsToShow: _months, columnZoom: _zoom, ...tsRest } = ts;
		result.timeline_settings = {
			start_date: startDate,
			view_mode: 'custom',
			zoom_level: (ts.columnZoom as number) ?? 1.0,
			data: { ...tsRest, monthsToShow: ts.monthsToShow, columnZoom: ts.columnZoom },
		};
	}

	return result;
}
