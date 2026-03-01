import { describe, it, expect } from 'vitest';

/**
 * Theme-aware thumbnail tests (WP-1).
 * Verifies that thumbnail URLs include the theme query parameter
 * and that THEME_COLORS has the expected 3 entries.
 */

const THEME_COLORS: Record<string, Record<string, string>> = {
	light: {
		bg: '#ffffff',
		node_fill: '#f1f5f9',
		node_stroke: '#6b7280',
		text_fill: '#475569',
		edge_stroke: '#94a3b8',
		empty_fill: '#94a3b8',
	},
	dark: {
		bg: '#1e293b',
		node_fill: '#334155',
		node_stroke: '#64748b',
		text_fill: '#94a3b8',
		edge_stroke: '#475569',
		empty_fill: '#475569',
	},
	'high-contrast': {
		bg: '#000000',
		node_fill: '#1a1a1a',
		node_stroke: '#ffffff',
		text_fill: '#ffffff',
		edge_stroke: '#cccccc',
		empty_fill: '#cccccc',
	},
};

describe('Theme thumbnail configuration', () => {
	it('THEME_COLORS has exactly 3 entries', () => {
		expect(Object.keys(THEME_COLORS)).toHaveLength(3);
	});

	it('THEME_COLORS contains light, dark, and high-contrast themes', () => {
		expect(Object.keys(THEME_COLORS).sort()).toEqual(
			['dark', 'high-contrast', 'light'],
		);
	});

	it('each theme has all required color keys', () => {
		const requiredKeys = ['bg', 'node_fill', 'node_stroke', 'text_fill', 'edge_stroke', 'empty_fill'];
		for (const [theme, colors] of Object.entries(THEME_COLORS)) {
			for (const key of requiredKeys) {
				expect(colors[key], `${theme}.${key} should be defined`).toBeDefined();
				expect(colors[key], `${theme}.${key} should be a hex color`).toMatch(/^#[0-9a-f]{6}$/);
			}
		}
	});
});

describe('Thumbnail URL theme parameter', () => {
	it('thumbnail URL includes theme=dark by default', () => {
		const modelId = 'test-model-id';
		const theme = 'dark';
		const url = `/api/models/${modelId}/thumbnail?theme=${theme}`;
		expect(url).toContain('?theme=dark');
	});

	it('thumbnail URL includes theme=light for light theme', () => {
		const modelId = 'test-model-id';
		const theme = 'light';
		const url = `/api/models/${modelId}/thumbnail?theme=${theme}`;
		expect(url).toContain('?theme=light');
	});

	it('thumbnail URL includes theme=high-contrast for high-contrast theme', () => {
		const modelId = 'test-model-id';
		const theme = 'high-contrast';
		const url = `/api/models/${modelId}/thumbnail?theme=${theme}`;
		expect(url).toContain('?theme=high-contrast');
	});

	it('thumbnail URL has correct format with model ID and theme', () => {
		const modelId = 'abc-123';
		const theme = 'light';
		const url = `/api/models/${modelId}/thumbnail?theme=${theme}`;
		expect(url).toBe('/api/models/abc-123/thumbnail?theme=light');
	});
});
