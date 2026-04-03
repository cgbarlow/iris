/** Colour palette and labels for knowledge graph (ADR-116). */

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

export function defaultGraphSettings(): { nodes: Record<string, boolean>; edges: Record<string, boolean> } {
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
	};
}

function _storageKey(scopeId: string): string {
	return `${STORAGE_PREFIX}:${scopeId}`;
}

export function loadGraphSettings(setId?: string, collectionId?: string): { nodes: Record<string, boolean>; edges: Record<string, boolean> } {
	if (typeof localStorage === 'undefined') return defaultGraphSettings();
	const defaults = defaultGraphSettings();

	// Start with global settings as base
	let base = defaults;
	try {
		const raw = localStorage.getItem(_storageKey('__global__'));
		if (raw) {
			const saved = JSON.parse(raw);
			base = {
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
					nodes: { ...base.nodes, ...saved.nodes },
					edges: { ...base.edges, ...saved.edges },
				};
			}
		} catch { /* ignore */ }
	}

	return base;
}

export function saveGraphSettings(settings: { nodes: Record<string, boolean>; edges: Record<string, boolean> }, scopeId?: string): void {
	if (typeof localStorage !== 'undefined') {
		localStorage.setItem(_storageKey(scopeId || '__global__'), JSON.stringify(settings));
	}
}
