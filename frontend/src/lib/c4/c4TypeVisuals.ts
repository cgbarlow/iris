/**
 * C4 Type Glyphs — SVG path data and metadata for all 9 C4 entity types.
 *
 * Colours are intentionally omitted; they come from the active theme.
 */

export interface C4TypeGlyphData {
	label: string;
	viewBox: string;
	path: string;
	description: string;
}

export const C4_TYPE_GLYPHS: Record<string, C4TypeGlyphData> = {
	person: {
		label: 'Person',
		viewBox: '0 0 24 24',
		path: '<circle cx="12" cy="7" r="4" /><path d="M5.5 21a6.5 6.5 0 0 1 13 0" />',
		description: 'A user or actor interacting with the system',
	},
	software_system: {
		label: 'Software System',
		viewBox: '0 0 24 24',
		path: '<rect x="3" y="4" width="18" height="16" rx="3" />',
		description: 'An overall software system (internal)',
	},
	software_system_external: {
		label: 'External System',
		viewBox: '0 0 24 24',
		path: '<circle cx="12" cy="12" r="9" /><ellipse cx="12" cy="12" rx="9" ry="4" /><path d="M12 3 v18" /><path d="M3.5 8.5 Q12 12 20.5 8.5" /><path d="M3.5 15.5 Q12 12 20.5 15.5" />',
		description: 'An external system outside your control',
	},
	container: {
		label: 'Container',
		viewBox: '0 0 24 24',
		path: '<path d="M4 7 L4 19 L16 19 L16 7 Z" /><path d="M4 7 L8 3 L20 3 L16 7" /><path d="M16 7 L20 3 L20 15 L16 19" />',
		description: 'An application, data store, or service',
	},
	c4_component: {
		label: 'Component',
		viewBox: '0 0 24 24',
		path: '<rect x="5" y="3" width="14" height="18" rx="1" /><rect x="2" y="7" width="6" height="3" rx="1" /><rect x="2" y="14" width="6" height="3" rx="1" />',
		description: 'A module or service within a container',
	},
	code_element: {
		label: 'Code Element',
		viewBox: '0 0 24 24',
		path: '<polyline points="8 6 3 12 8 18" /><polyline points="16 6 21 12 16 18" />',
		description: 'A class, interface, or function',
	},
	deployment_node: {
		label: 'Deployment Node',
		viewBox: '0 0 24 24',
		path: '<rect x="2" y="2" width="20" height="8" rx="2" /><rect x="2" y="14" width="20" height="8" rx="2" /><circle cx="6" cy="6" r="1" fill="currentColor" /><circle cx="6" cy="18" r="1" fill="currentColor" />',
		description: 'Server, VM, container platform, or cloud region',
	},
	infrastructure_node: {
		label: 'Infrastructure Node',
		viewBox: '0 0 24 24',
		path: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />',
		description: 'Load balancer, firewall, or DNS',
	},
	container_instance: {
		label: 'Container Instance',
		viewBox: '0 0 24 24',
		path: '<rect x="2" y="6" width="14" height="14" rx="2" /><rect x="8" y="2" width="14" height="14" rx="2" />',
		description: 'Running instance of a container',
	},
};
