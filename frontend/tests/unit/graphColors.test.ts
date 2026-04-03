import { describe, it, expect } from 'vitest';
import { getNodeTypeColor, defaultGraphSettings } from '../../src/lib/utils/graphColors';

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
});
