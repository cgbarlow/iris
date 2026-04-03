import { describe, it, expect } from 'vitest';
import { getNodeTypeColor, defaultGraphSettings, clearUserOverrides } from '../../src/lib/utils/graphColors';

describe('getNodeTypeColor', () => {
	it('returns blue for elements', () => {
		expect(getNodeTypeColor('element')).toBe('#3b82f6');
	});

	it('returns green for diagrams', () => {
		expect(getNodeTypeColor('diagram')).toBe('#22c55e');
	});

	it('returns amber for packages', () => {
		expect(getNodeTypeColor('package')).toBe('#f59e0b');
	});

	it('returns grey for unknown types', () => {
		expect(getNodeTypeColor('unknown')).toBe('#6b7280');
	});
});

describe('defaultGraphSettings', () => {
	it('has all node types enabled', () => {
		const s = defaultGraphSettings();
		expect(s.nodes.element).toBe(true);
		expect(s.nodes.diagram).toBe(true);
		expect(s.nodes.package).toBe(true);
		expect(s.nodes.collection).toBe(true);
		expect(s.nodes.set).toBe(true);
	});

	it('has all edge types enabled', () => {
		const s = defaultGraphSettings();
		const expectedEdges = [
			'collection_membership', 'set_membership', 'direct_diagram_links',
			'hierarchy', 'diagram_element', 'diagram_package',
			'diagram_link', 'package_relationship', 'element_relationship',
		];
		for (const key of expectedEdges) {
			expect(s.edges[key], `${key} should default to true`).toBe(true);
		}
	});

	it('has label_density defaulting to 10', () => {
		const s = defaultGraphSettings();
		expect(s.label_density).toBe(10);
	});

	it('has node_spacing defaulting to 1.0', () => {
		const s = defaultGraphSettings();
		expect(s.node_spacing).toBe(1.0);
	});

	it('has size_contrast defaulting to 1.0', () => {
		const s = defaultGraphSettings();
		expect(s.size_contrast).toBe(1.0);
	});

	it('has link_length defaulting to 1.0', () => {
		const s = defaultGraphSettings();
		expect(s.link_length).toBe(1.0);
	});
});

describe('clearUserOverrides', () => {
	it('does not throw when called without arguments', () => {
		expect(() => clearUserOverrides()).not.toThrow();
	});

	it('does not throw when called with a scopeId', () => {
		expect(() => clearUserOverrides('some-scope')).not.toThrow();
	});

	it('removes the correct localStorage key', () => {
		const storage: Record<string, string> = { 'iris-graph-settings:test-scope': '{}' };
		globalThis.localStorage = {
			getItem: (key: string) => storage[key] ?? null,
			setItem: (key: string, value: string) => { storage[key] = value; },
			removeItem: (key: string) => { delete storage[key]; },
			clear: () => { Object.keys(storage).forEach(k => delete storage[k]); },
			length: 0,
			key: () => null,
		};
		clearUserOverrides('test-scope');
		expect(storage['iris-graph-settings:test-scope']).toBeUndefined();
	});

	it('removes global key when no scopeId provided', () => {
		const storage: Record<string, string> = { 'iris-graph-settings:__global__': '{}' };
		globalThis.localStorage = {
			getItem: (key: string) => storage[key] ?? null,
			setItem: (key: string, value: string) => { storage[key] = value; },
			removeItem: (key: string) => { delete storage[key]; },
			clear: () => { Object.keys(storage).forEach(k => delete storage[k]); },
			length: 0,
			key: () => null,
		};
		clearUserOverrides();
		expect(storage['iris-graph-settings:__global__']).toBeUndefined();
	});
});
