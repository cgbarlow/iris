// @ts-nocheck — Node.js imports not typed under SvelteKit tsconfig; Vitest resolves them correctly at runtime.
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

/**
 * Tests for icon infrastructure (ADR-091-B).
 *
 * Verifies icon registry, tags index, and IconDisplay component exist
 * and have correct structure.
 */

const ICONS_DIR = resolve(__dirname, '../../src/lib/icons');

describe('Icon registry (ADR-091-B)', () => {
	it('iconRegistry.ts exports resolveIcon and isValidIcon', () => {
		const source = readFileSync(resolve(ICONS_DIR, 'iconRegistry.ts'), 'utf-8');
		expect(source).toContain('export function resolveIcon');
		expect(source).toContain('export function isValidIcon');
	});

	it('iconRegistry.ts imports from lucide-svelte', () => {
		const source = readFileSync(resolve(ICONS_DIR, 'iconRegistry.ts'), 'utf-8');
		expect(source).toContain('lucide-svelte');
	});

	it('iconTags.ts exports ICON_TAGS and ICON_TAG_INDEX', () => {
		const source = readFileSync(resolve(ICONS_DIR, 'iconTags.ts'), 'utf-8');
		expect(source).toContain('export const ICON_TAGS');
		expect(source).toContain('export const ICON_TAG_INDEX');
	});

	it('iconTags.json contains valid JSON array of icon entries', () => {
		const json = readFileSync(resolve(ICONS_DIR, 'iconTags.json'), 'utf-8');
		const entries = JSON.parse(json);
		expect(Array.isArray(entries)).toBe(true);
		expect(entries.length).toBeGreaterThan(50);
		// Each entry should have name, tags, and category
		for (const entry of entries) {
			expect(entry).toHaveProperty('name');
			expect(entry).toHaveProperty('tags');
			expect(entry).toHaveProperty('category');
			expect(Array.isArray(entry.tags)).toBe(true);
			expect(entry.tags.length).toBeGreaterThan(0);
		}
	});

	it('IconDisplay.svelte exists and imports from iconRegistry', () => {
		const source = readFileSync(resolve(ICONS_DIR, 'IconDisplay.svelte'), 'utf-8');
		expect(source).toContain('resolveIcon');
		expect(source).toContain('IconRef');
	});

	it('canvas.ts defines IconRef type', () => {
		const source = readFileSync(resolve(__dirname, '../../src/lib/types/canvas.ts'), 'utf-8');
		expect(source).toContain('export interface IconRef');
		expect(source).toMatch(/set:\s*'lucide'/);
	});

	it('NodeVisualOverrides includes icon field', () => {
		const source = readFileSync(resolve(__dirname, '../../src/lib/types/canvas.ts'), 'utf-8');
		expect(source).toContain('icon?: IconRef');
	});

	it('NavigationCellNode imports IconDisplay', () => {
		const source = readFileSync(
			resolve(__dirname, '../../src/lib/canvas/nodes/NavigationCellNode.svelte'),
			'utf-8',
		);
		expect(source).toContain('IconDisplay');
	});
});
