/**
 * Global view store — manages the active admin-configurable view.
 * Views control which UI features are visible (toolbar items, metadata sections, canvas options).
 */

import { apiFetch } from '$lib/utils/api';

export interface ViewConfig {
	toolbar: {
		element_types?: string[];
		relationship_types?: string[];
		show_routing_type?: boolean;
		show_edge_properties?: boolean;
	};
	metadata: {
		show_overview?: boolean;
		show_details?: boolean;
		show_extended?: boolean;
	};
	canvas: {
		show_cardinality?: boolean;
		show_role_names?: boolean;
		show_stereotypes?: boolean;
		show_description_on_nodes?: boolean;
		sort_attributes?: 'pos' | 'alpha';
	};
}

export interface View {
	id: string;
	name: string;
	description: string | null;
	config: ViewConfig;
	is_default: boolean;
	created_at: string;
	updated_at: string;
}

let views = $state<View[]>([]);
let activeViewId = $state<string>(
	typeof localStorage !== 'undefined' ? (localStorage.getItem('iris_active_view') ?? 'advanced') : 'advanced'
);

export function getViews(): View[] {
	return views;
}

export function getActiveViewId(): string {
	return activeViewId;
}

export function getActiveView(): View | undefined {
	return views.find((v) => v.id === activeViewId);
}

export function getActiveConfig(): ViewConfig {
	const view = getActiveView();
	return view?.config ?? {
		toolbar: { show_routing_type: true, show_edge_properties: true },
		metadata: { show_overview: true, show_details: true, show_extended: true },
		canvas: { show_cardinality: true, show_role_names: true, show_stereotypes: true, show_description_on_nodes: true },
	};
}

export function setActiveView(viewId: string): void {
	activeViewId = viewId;
	localStorage.setItem('iris_active_view', viewId);
}

export async function loadViews(): Promise<void> {
	try {
		views = await apiFetch<View[]>('/api/views');
	} catch {
		views = [];
	}
}
