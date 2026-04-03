/** Colour palette and labels for knowledge graph (ADR-116). */

import type { GraphSettings } from '$lib/types/api';

const NODE_TYPE_COLORS: Record<string, string> = {
	collection: '#ef4444', // red
	set: '#8b5cf6',        // violet
	package: '#f59e0b',    // amber
	diagram: '#22c55e',    // green
	element: '#3b82f6',    // blue
};

export function getNodeTypeColor(nodeType: string): string {
	return NODE_TYPE_COLORS[nodeType] ?? '#6b7280';
}

export const EDGE_TYPE_LABELS: Record<string, string> = {
	collection_membership: 'Collection → Sets',
	set_membership: 'Set → Contents',
	hierarchy: 'Package Nesting',
	diagram_element: 'Diagram Elements',
	diagram_package: 'Diagram References',
	diagram_link: 'Diagram Navigation',
	package_relationship: 'Package Relationships',
	element_relationship: 'Element Relationships',
};

export const NODE_TYPE_LABELS: Record<string, string> = {
	collection: 'Collections',
	set: 'Sets',
	package: 'Packages',
	diagram: 'Diagrams',
	element: 'Elements',
};

const STORAGE_PREFIX = 'iris-graph-settings';

export function defaultGraphSettings(): GraphSettings {
	return {
		nodes: { collection: true, set: true, package: true, diagram: true, element: true },
		edges: {
			collection_membership: true,
			set_membership: true,
			direct_diagram_links: true,
			hierarchy: true,
			diagram_element: true,
			diagram_package: true,
			diagram_link: true,
			package_relationship: true,
			element_relationship: true,
		},
		label_density: 10,
		node_spacing: 1.0,
		size_contrast: 1.0,
		link_length: 1.0,
	};
}

function _storageKey(scopeId: string): string {
	return `${STORAGE_PREFIX}:${scopeId}`;
}

export async function fetchAdminDefaults(setId?: string, collectionId?: string): Promise<GraphSettings> {
	try {
		const params = new URLSearchParams();
		if (setId) params.set('set_id', setId);
		if (collectionId) params.set('collection_id', collectionId);
		const { apiFetch } = await import('$lib/utils/api');
		const resp = await apiFetch<{ settings: GraphSettings }>(`/api/graph/settings?${params}`);
		return { ...defaultGraphSettings(), ...resp.settings };
	} catch {
		return defaultGraphSettings();
	}
}

/**
 * One-time migration: push existing localStorage graph settings to the DB
 * as admin defaults so they survive a "Reset". Only runs for admins,
 * only for scopes that have localStorage data, and marks itself done
 * so it never runs twice.
 */
export async function migrateLocalSettingsToAdmin(): Promise<void> {
	if (typeof localStorage === 'undefined') return;
	const MIGRATED_KEY = 'iris-graph-settings-migrated';
	if (localStorage.getItem(MIGRATED_KEY)) return;

	try {
		const { apiFetch } = await import('$lib/utils/api');

		// Find all localStorage keys for graph settings
		const keys: string[] = [];
		for (let i = 0; i < localStorage.length; i++) {
			const k = localStorage.key(i);
			if (k?.startsWith(STORAGE_PREFIX + ':')) keys.push(k);
		}

		// Fetch existing collections and sets to determine scope type for UUIDs
		let collectionIds = new Set<string>();
		let setIds = new Set<string>();
		try {
			const cols = await apiFetch<{ items: { id: string }[] }>('/api/collections');
			collectionIds = new Set(cols.items.map((c) => c.id));
			const sets = await apiFetch<{ items: { id: string }[] }>('/api/sets');
			setIds = new Set(sets.items.map((s) => s.id));
		} catch { /* ignore */ }

		for (const key of keys) {
			const raw = localStorage.getItem(key);
			if (!raw) continue;
			const scopeId = key.slice(STORAGE_PREFIX.length + 1);

			let scopeType: string;
			if (scopeId === '__global__') scopeType = 'global';
			else if (collectionIds.has(scopeId)) scopeType = 'collection';
			else if (setIds.has(scopeId)) scopeType = 'set';
			else continue; // unknown scope — skip

			try {
				const saved = JSON.parse(raw);
				const settings = { ...defaultGraphSettings(), ...saved, nodes: { ...defaultGraphSettings().nodes, ...saved.nodes }, edges: { ...defaultGraphSettings().edges, ...saved.edges } };
				await apiFetch('/api/graph/settings', {
					method: 'PUT',
					body: JSON.stringify({ scope_type: scopeType, scope_id: scopeId, settings }),
				});
			} catch { /* ignore individual failures */ }
		}
	} catch { /* ignore — not admin or not authenticated */ }

	localStorage.setItem(MIGRATED_KEY, 'true');
}

export function clearUserOverrides(scopeId?: string): void {
	if (typeof localStorage !== 'undefined') {
		localStorage.removeItem(`iris-graph-settings:${scopeId || '__global__'}`);
	}
}

export function loadGraphSettings(setId?: string, collectionId?: string, adminDefaults?: GraphSettings): GraphSettings {
	if (typeof localStorage === 'undefined') return adminDefaults ?? defaultGraphSettings();
	const defaults = adminDefaults ?? defaultGraphSettings();

	// Start with global settings as base
	let base = defaults;
	try {
		const raw = localStorage.getItem(_storageKey('__global__'));
		if (raw) {
			const saved = JSON.parse(raw);
			base = {
				...defaults,
				...saved,
				nodes: { ...defaults.nodes, ...saved.nodes },
				edges: { ...defaults.edges, ...saved.edges },
			};
		}
	} catch { /* ignore */ }

	// Override with collection-level settings if available
	if (collectionId) {
		try {
			const raw = localStorage.getItem(_storageKey(collectionId));
			if (raw) {
				const saved = JSON.parse(raw);
				base = {
					...defaults,
					...saved,
					nodes: { ...defaults.nodes, ...saved.nodes },
					edges: { ...defaults.edges, ...saved.edges },
				};
			}
		} catch { /* ignore */ }
	}

	// Override with set-level settings if available
	if (setId) {
		try {
			const raw = localStorage.getItem(_storageKey(setId));
			if (raw) {
				const saved = JSON.parse(raw);
				return {
					...base,
					...saved,
					nodes: { ...base.nodes, ...saved.nodes },
					edges: { ...base.edges, ...saved.edges },
				};
			}
		} catch { /* ignore */ }
	}

	return base;
}

export function saveGraphSettings(settings: GraphSettings, scopeId?: string): void {
	if (typeof localStorage !== 'undefined') {
		localStorage.setItem(_storageKey(scopeId || '__global__'), JSON.stringify(settings));
	}
}
