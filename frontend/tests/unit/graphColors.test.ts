import { describe, it, expect } from 'vitest';
import { getNodeTypeColor, defaultGraphSettings, EDGE_TYPE_LABELS } from '../../src/lib/utils/graphColors';

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
	});

	it('has all edge types enabled', () => {
		const s = defaultGraphSettings();
		for (const key of Object.keys(EDGE_TYPE_LABELS)) {
			expect(s.edges[key]).toBe(true);
		}
	});
});
